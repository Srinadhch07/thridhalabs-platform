"""Work showcase tests.

Covers member CRUD, slug generation, publication transitions, media ownership,
content limits, member media library and the composite public-visibility rules
(work + owner profile).
"""

from __future__ import annotations

from httpx import ASGITransport, AsyncClient

from app.main import app
from tests._content_helpers import (
    capture_onboarding_token,
    complete_member_profile,
    create_work,
    login_admin,
    member_login,
    onboard_member,
    patch_work,
    png_bytes,
    publish_work,
    upload_member_media,
)


def _second_client() -> AsyncClient:
    return AsyncClient(transport=ASGITransport(app=app), base_url="https://testserver")


async def _login_admin(client, make_admin, fetch_csrf, email="owner@example.com") -> str:
    return await login_admin(client, make_admin, fetch_csrf, email=email)


async def _setup_member(
    admin_client,
    make_admin,
    fetch_csrf,
    monkeypatch,
    *,
    email: str,
    admin_token: str,
    visibility: str | None = None,
    full_name: str = "Member Person",
):
    member_client = _second_client()
    capture = capture_onboarding_token(monkeypatch)
    readable_id, member_token = await onboard_member(
        member_client,
        admin_client,
        admin_token,
        capture,
        email=email,
        full_name=full_name,
        visibility=visibility,
    )
    return member_client, member_token, readable_id


# ---------------------------------------------------------------------------
# CRUD + defaults
# ---------------------------------------------------------------------------
async def test_create_work_defaults(client, make_admin, fetch_csrf, monkeypatch):
    admin_token = await _login_admin(client, make_admin, fetch_csrf)
    member_client, token, _ = await _setup_member(
        client, make_admin, fetch_csrf, monkeypatch,
        email="creator@example.com", admin_token=admin_token,
    )
    work = await create_work(member_client, token, title="Hello World")
    assert work["slug"] == "hello-world"
    assert work["publication_status"] == "draft"
    assert work["visibility"] == "private"
    assert work["version"] == 0
    assert work["cover_media_id"] is None
    assert work["content"]["version"] == 1
    assert len(work["content"]["blocks"]) == 1  # blank-canvas seed


async def test_create_work_template_seeds_blocks(client, make_admin, fetch_csrf, monkeypatch):
    admin_token = await _login_admin(client, make_admin, fetch_csrf)
    member_client, token, _ = await _setup_member(
        client, make_admin, fetch_csrf, monkeypatch,
        email="tmpl@example.com", admin_token=admin_token,
    )
    work = await create_work(member_client, token, template="research")
    types = [block["type"] for block in work["content"]["blocks"]]
    assert types[0] == "heading"
    assert "quote" in types


async def test_create_work_rejects_unknown_template(client, make_admin, fetch_csrf, monkeypatch):
    admin_token = await _login_admin(client, make_admin, fetch_csrf)
    member_client, token, _ = await _setup_member(
        client, make_admin, fetch_csrf, monkeypatch,
        email="badtmpl@example.com", admin_token=admin_token,
    )
    res = await member_client.post(
        "/api/member/works",
        json={"title": "X", "summary": "Y", "template": "nope"},
        headers={"X-CSRF-Token": token},
    )
    assert res.status_code == 422


async def test_create_work_requires_csrf(client, make_admin, fetch_csrf, monkeypatch):
    admin_token = await _login_admin(client, make_admin, fetch_csrf)
    member_client, _token, _ = await _setup_member(
        client, make_admin, fetch_csrf, monkeypatch,
        email="nocsrf@example.com", admin_token=admin_token,
    )
    res = await member_client.post(
        "/api/member/works", json={"title": "X", "summary": "Y"}
    )
    assert res.status_code == 403


async def test_slug_is_unique_per_member(client, make_admin, fetch_csrf, monkeypatch):
    admin_token = await _login_admin(client, make_admin, fetch_csrf)
    member_client, token, _ = await _setup_member(
        client, make_admin, fetch_csrf, monkeypatch,
        email="slug@example.com", admin_token=admin_token,
    )
    first = await create_work(member_client, token, title="Same Title")
    second = await create_work(member_client, token, title="Same Title")
    assert first["slug"] == "same-title"
    assert second["slug"] == "same-title-2"


async def test_update_work_patch_and_version(client, make_admin, fetch_csrf, monkeypatch):
    admin_token = await _login_admin(client, make_admin, fetch_csrf)
    member_client, token, _ = await _setup_member(
        client, make_admin, fetch_csrf, monkeypatch,
        email="patch@example.com", admin_token=admin_token,
    )
    work = await create_work(member_client, token, title="Original", tags=["a"])
    updated = await patch_work(member_client, token, work["id"], summary="New summary")
    assert updated["summary"] == "New summary"
    assert updated["title"] == "Original"  # untouched
    assert updated["tags"] == ["a"]  # untouched
    assert updated["version"] == 1

    renamed = await patch_work(member_client, token, work["id"], title="Renamed")
    assert renamed["slug"] == "renamed"


async def test_work_isolation_between_members(client, make_admin, fetch_csrf, monkeypatch):
    admin_token = await _login_admin(client, make_admin, fetch_csrf)
    a_client, a_token, _ = await _setup_member(
        client, make_admin, fetch_csrf, monkeypatch,
        email="a@example.com", admin_token=admin_token,
    )
    b_client = _second_client()
    capture = capture_onboarding_token(monkeypatch)
    _b_readable, b_token = await onboard_member(
        b_client, client, admin_token, capture, email="b@example.com"
    )
    await create_work(a_client, a_token, title="Private to A")

    a_list = await a_client.get("/api/member/works")
    b_list = await b_client.get("/api/member/works")
    assert a_list.json()["total"] == 1
    assert b_list.json()["total"] == 0
    del b_token


async def test_get_work_404_for_non_owner(client, make_admin, fetch_csrf, monkeypatch):
    admin_token = await _login_admin(client, make_admin, fetch_csrf)
    a_client, a_token, _ = await _setup_member(
        client, make_admin, fetch_csrf, monkeypatch,
        email="a2@example.com", admin_token=admin_token,
    )
    b_client = _second_client()
    capture = capture_onboarding_token(monkeypatch)
    _b_readable, b_token = await onboard_member(
        b_client, client, admin_token, capture, email="b2@example.com"
    )
    work = await create_work(a_client, a_token, title="A owned")

    res = await b_client.get(f"/api/member/works/{work['id']}")
    assert res.status_code == 404
    del b_token


# ---------------------------------------------------------------------------
# Publication
# ---------------------------------------------------------------------------
async def test_publish_unpublish_sets_published_at_once(client, make_admin, fetch_csrf, monkeypatch):
    admin_token = await _login_admin(client, make_admin, fetch_csrf)
    member_client, token, _ = await _setup_member(
        client, make_admin, fetch_csrf, monkeypatch,
        email="pub@example.com", admin_token=admin_token,
    )
    work = await create_work(member_client, token)
    published = await publish_work(member_client, token, work["id"])
    assert published["publication_status"] == "published"
    first_published_at = published["published_at"]
    assert first_published_at is not None

    res = await member_client.post(
        f"/api/member/works/{work['id']}/unpublish",
        headers={"X-CSRF-Token": token},
    )
    assert res.status_code == 200
    assert res.json()["publication_status"] == "unpublished"

    republished = await publish_work(member_client, token, work["id"])
    assert republished["published_at"] == first_published_at  # not overwritten


# ---------------------------------------------------------------------------
# Media ownership
# ---------------------------------------------------------------------------
async def test_cover_media_must_be_owned(client, make_admin, fetch_csrf, monkeypatch):
    admin_token = await _login_admin(client, make_admin, fetch_csrf)
    a_client, a_token, _ = await _setup_member(
        client, make_admin, fetch_csrf, monkeypatch,
        email="ma@example.com", admin_token=admin_token,
    )
    b_client = _second_client()
    capture = capture_onboarding_token(monkeypatch)
    _b_readable, b_token = await onboard_member(
        b_client, client, admin_token, capture, email="mb@example.com"
    )
    a_media = await upload_member_media(a_client, a_token)
    res = await b_client.post(
        "/api/member/works",
        json={"title": "Borrow", "summary": "s", "cover_media_id": a_media["id"]},
        headers={"X-CSRF-Token": b_token},
    )
    assert res.status_code == 422
    assert res.json()["error"]["code"] == "MEDIA_NOT_OWNED"


async def test_own_cover_media_accepted(client, make_admin, fetch_csrf, monkeypatch):
    admin_token = await _login_admin(client, make_admin, fetch_csrf)
    member_client, token, _ = await _setup_member(
        client, make_admin, fetch_csrf, monkeypatch,
        email="ownmedia@example.com", admin_token=admin_token,
    )
    media = await upload_member_media(member_client, token)
    work = await create_work(member_client, token, cover_media_id=media["id"])
    assert work["cover_media_id"] == media["id"]


async def test_member_media_list_is_own_only(client, make_admin, fetch_csrf, monkeypatch):
    admin_token = await _login_admin(client, make_admin, fetch_csrf)
    a_client, a_token, _ = await _setup_member(
        client, make_admin, fetch_csrf, monkeypatch,
        email="la@example.com", admin_token=admin_token,
    )
    b_client = _second_client()
    capture = capture_onboarding_token(monkeypatch)
    _b_readable, b_token = await onboard_member(
        b_client, client, admin_token, capture, email="lb@example.com"
    )
    await upload_member_media(a_client, a_token)
    await upload_member_media(b_client, b_token, data=png_bytes(color="red"))

    listing = await a_client.get("/api/member/media")
    assert listing.status_code == 200
    assert listing.json()["total"] == 1


# ---------------------------------------------------------------------------
# Content limits
# ---------------------------------------------------------------------------
async def test_content_block_limit_enforced(client, make_admin, fetch_csrf, monkeypatch):
    admin_token = await _login_admin(client, make_admin, fetch_csrf)
    member_client, token, _ = await _setup_member(
        client, make_admin, fetch_csrf, monkeypatch,
        email="blocks@example.com", admin_token=admin_token,
    )
    blocks = [
        {"type": "paragraph", "spans": [{"text": "x"}]} for _ in range(101)
    ]
    res = await member_client.post(
        "/api/member/works",
        json={
            "title": "Too many",
            "summary": "s",
            "content": {"version": 1, "blocks": blocks},
        },
        headers={"X-CSRF-Token": token},
    )
    assert res.status_code == 422


async def test_content_requires_http_urls(client, make_admin, fetch_csrf, monkeypatch):
    admin_token = await _login_admin(client, make_admin, fetch_csrf)
    member_client, token, _ = await _setup_member(
        client, make_admin, fetch_csrf, monkeypatch,
        email="links@example.com", admin_token=admin_token,
    )
    res = await member_client.post(
        "/api/member/works",
        json={
            "title": "Bad link",
            "summary": "s",
            "external_links": [{"label": "Bad", "url": "javascript:alert(1)"}],
        },
        headers={"X-CSRF-Token": token},
    )
    assert res.status_code == 422


# ---------------------------------------------------------------------------
# Update content (regression: PATCH must validate the nested model, not a dict)
# ---------------------------------------------------------------------------
async def test_update_work_accepts_content_dict(client, make_admin, fetch_csrf, monkeypatch):
    """Regression: a PATCH sends content as a JSON object (the editor/autosave
    payload). `model_dump` used to hand `_validate_content` a plain dict, which
    raised `AttributeError: 'dict' object has no attribute 'blocks'` (HTTP 500).
    The update must validate the nested ContentDocument and persist it."""
    admin_token = await _login_admin(client, make_admin, fetch_csrf)
    member_client, token, _ = await _setup_member(
        client, make_admin, fetch_csrf, monkeypatch,
        email="patchcontent@example.com", admin_token=admin_token,
    )
    work = await create_work(member_client, token, title="Editable")
    updated = await patch_work(
        member_client,
        token,
        work["id"],
        content={
            "version": 1,
            "blocks": [
                {"type": "heading", "level": 2, "text": "Overview"},
                {"type": "paragraph", "spans": [{"text": "Hello", "bold": True}]},
            ],
        },
    )
    assert updated["version"] == 1
    assert [block["type"] for block in updated["content"]["blocks"]] == [
        "heading",
        "paragraph",
    ]
    assert updated["content"]["blocks"][1]["spans"][0]["text"] == "Hello"

    # Round-trips through the read path too.
    fetched = await member_client.get(f"/api/member/works/{work['id']}")
    assert fetched.status_code == 200, fetched.text
    assert len(fetched.json()["content"]["blocks"]) == 2


async def test_update_work_content_total_text_limit_enforced(
    client, make_admin, fetch_csrf, monkeypatch
):
    """The service's aggregate text limit runs (with a real model) on update,
    not only on create."""
    admin_token = await _login_admin(client, make_admin, fetch_csrf)
    member_client, token, _ = await _setup_member(
        client, make_admin, fetch_csrf, monkeypatch,
        email="patchtext@example.com", admin_token=admin_token,
    )
    work = await create_work(member_client, token, title="Huge on patch")
    blocks = [
        {"type": "heading", "level": 2, "text": "x" * 10_000} for _ in range(11)
    ]
    res = await member_client.patch(
        f"/api/member/works/{work['id']}",
        json={"content": {"version": 1, "blocks": blocks}},
        headers={"X-CSRF-Token": token},
    )
    assert res.status_code == 422, res.text
    assert res.json()["error"]["code"] == "CONTENT_TOO_LARGE"


async def test_update_work_invalid_content_block_rejected(
    client, make_admin, fetch_csrf, monkeypatch
):
    """Malformed content is a controlled validation error (422), never an
    unhandled AttributeError/500."""
    admin_token = await _login_admin(client, make_admin, fetch_csrf)
    member_client, token, _ = await _setup_member(
        client, make_admin, fetch_csrf, monkeypatch,
        email="patchbad@example.com", admin_token=admin_token,
    )
    work = await create_work(member_client, token, title="Bad on patch")
    res = await member_client.patch(
        f"/api/member/works/{work['id']}",
        json={"content": {"version": 1, "blocks": [{"type": "unknown"}]}},
        headers={"X-CSRF-Token": token},
    )
    assert res.status_code == 422, res.text


async def test_update_work_content_media_must_be_owned(
    client, make_admin, fetch_csrf, monkeypatch
):
    """Referenced media inside updated content is still ownership-checked."""
    admin_token = await _login_admin(client, make_admin, fetch_csrf)
    a_client, a_token, _ = await _setup_member(
        client, make_admin, fetch_csrf, monkeypatch,
        email="wm-a@example.com", admin_token=admin_token,
    )
    b_client = _second_client()
    capture = capture_onboarding_token(monkeypatch)
    _b_readable, b_token = await onboard_member(
        b_client, client, admin_token, capture, email="wm-b@example.com"
    )
    a_media = await upload_member_media(a_client, a_token)
    work = await create_work(b_client, b_token, title="Borrow media")
    res = await b_client.patch(
        f"/api/member/works/{work['id']}",
        json={
            "content": {
                "version": 1,
                "blocks": [{"type": "image", "media_id": a_media["id"]}],
            }
        },
        headers={"X-CSRF-Token": b_token},
    )
    assert res.status_code == 422, res.text
    assert res.json()["error"]["code"] == "MEDIA_NOT_OWNED"


# ---------------------------------------------------------------------------
# Public visibility
# ---------------------------------------------------------------------------
async def _make_public_member(client, make_admin, fetch_csrf, monkeypatch, *, email):
    admin_token = await _login_admin(client, make_admin, fetch_csrf)
    member_client, token, readable = await _setup_member(
        client, make_admin, fetch_csrf, monkeypatch,
        email=email, admin_token=admin_token, visibility="public",
    )
    return member_client, token, readable


async def test_public_work_visibility_composite(client, make_admin, fetch_csrf, monkeypatch):
    member_client, token, readable = await _make_public_member(
        client, make_admin, fetch_csrf, monkeypatch, email="pubmember@example.com"
    )
    work = await create_work(member_client, token, title="Public Piece")

    # Draft → not public.
    res = await client.get(f"/api/public/members/{readable}/works/{work['slug']}")
    assert res.status_code == 404

    # Published but visibility private → not public.
    await publish_work(member_client, token, work["id"])
    res = await client.get(f"/api/public/members/{readable}/works/{work['slug']}")
    assert res.status_code == 404

    # Publish + make public → reachable.
    await patch_work(member_client, token, work["id"], visibility="public")
    res = await client.get(f"/api/public/members/{readable}/works/{work['slug']}")
    assert res.status_code == 200, res.text
    body = res.json()
    assert body["title"] == "Public Piece"
    assert body["author"]["member_id"] == readable


async def test_private_profile_blocks_public_work(client, make_admin, fetch_csrf, monkeypatch):
    admin_token = await _login_admin(client, make_admin, fetch_csrf)
    member_client, token, readable = await _setup_member(
        client, make_admin, fetch_csrf, monkeypatch,
        email="privprofile@example.com", admin_token=admin_token,  # default private
    )
    work = await create_work(member_client, token, title="Hidden", visibility="public")
    await publish_work(member_client, token, work["id"])

    res = await client.get(f"/api/public/members/{readable}/works/{work['slug']}")
    assert res.status_code == 404
    profile = await client.get(f"/api/public/members/{readable}")
    assert profile.status_code == 404


async def test_public_profile_lists_only_public_works(client, make_admin, fetch_csrf, monkeypatch):
    member_client, token, readable = await _make_public_member(
        client, make_admin, fetch_csrf, monkeypatch, email="listpub@example.com"
    )
    shown = await create_work(member_client, token, title="Shown", visibility="public")
    await publish_work(member_client, token, shown["id"])
    hidden = await create_work(member_client, token, title="Hidden Draft")
    del hidden

    res = await client.get(f"/api/public/members/{readable}")
    assert res.status_code == 200, res.text
    body = res.json()
    titles = [item["title"] for item in body["works"]]
    assert titles == ["Shown"]


async def test_sitemap_includes_public_work(client, make_admin, fetch_csrf, monkeypatch, tmp_path):
    from app.core.config import get_settings

    monkeypatch.setenv("FRONTEND_URL", "https://thridhalabs.example")
    get_settings.cache_clear()
    try:
        member_client, token, readable = await _make_public_member(
            client, make_admin, fetch_csrf, monkeypatch, email="sitemap@example.com"
        )
        work = await create_work(member_client, token, title="Sitemap Work", visibility="public")
        await publish_work(member_client, token, work["id"])

        res = await client.get("/sitemap.xml")
        assert res.status_code == 200
        text = res.text
        assert f"/members/{readable}" in text
        assert f"/members/{readable}/works/{work['slug']}" in text
    finally:
        monkeypatch.undo()
        get_settings.cache_clear()
