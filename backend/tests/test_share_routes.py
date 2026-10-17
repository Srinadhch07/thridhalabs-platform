"""Integration tests for the `/share/...` crawler documents + preview images.

Verifies that:
- published/public entities return HTML carrying the full Open Graph and
  Twitter metadata, with absolute URLs built from `FRONTEND_URL`;
- the paired image route returns a real 1200x630 JPEG;
- drafts, private profiles and unpublished/private works return an identical
  404 that never leaks existence.
"""

from __future__ import annotations

import io

import pytest
from httpx import ASGITransport, AsyncClient
from PIL import Image

from app.core.config import get_settings
from app.main import app
from tests._content_helpers import (
    capture_onboarding_token,
    create_project,
    create_work,
    login_admin,
    onboard_member,
    patch_work,
    publish_work,
)

_PUBLIC_URL = "https://thridhalabs.example"

_REQUIRED_META = (
    "og:title",
    "og:description",
    "og:image",
    "og:image:alt",
    "og:url",
    "og:type",
    "twitter:card",
    "twitter:title",
    "twitter:description",
    "twitter:image",
)


@pytest.fixture
def public_frontend_url(monkeypatch):
    monkeypatch.setenv("FRONTEND_URL", _PUBLIC_URL)
    get_settings.cache_clear()
    yield
    monkeypatch.undo()
    get_settings.cache_clear()


def _second_client() -> AsyncClient:
    return AsyncClient(transport=ASGITransport(app=app), base_url="https://testserver")


async def _setup_member(client, make_admin, fetch_csrf, monkeypatch, *, email, visibility):
    admin_token = await login_admin(client, make_admin, fetch_csrf)
    member_client = _second_client()
    capture = capture_onboarding_token(monkeypatch)
    readable, token = await onboard_member(
        member_client,
        client,
        admin_token,
        capture,
        email=email,
        visibility=visibility,
    )
    return member_client, token, readable


def _assert_meta(html: str, canonical: str, image: str) -> None:
    for key in _REQUIRED_META:
        assert key in html, key
    assert "summary_large_image" in html
    assert canonical in html
    assert image in html


def _assert_jpeg(data: bytes) -> None:
    image = Image.open(io.BytesIO(data))
    assert image.format == "JPEG"
    assert image.size == (1200, 630)


async def test_member_share_document_and_image(
    client, make_admin, fetch_csrf, monkeypatch, public_frontend_url
):
    _member_client, _token, readable = await _setup_member(
        client, make_admin, fetch_csrf, monkeypatch,
        email="sharemember@example.com", visibility="public",
    )

    res = await client.get(f"/share/members/{readable}")
    assert res.status_code == 200, res.text
    assert res.headers["content-type"].startswith("text/html")
    canonical = f"{_PUBLIC_URL}/members/{readable}"
    image = f"{_PUBLIC_URL}/share/members/{readable}/image"
    _assert_meta(res.text, canonical, image)
    assert "localhost" not in res.text

    img = await client.get(f"/share/members/{readable}/image")
    assert img.status_code == 200, img.text
    assert img.headers["content-type"] == "image/jpeg"
    _assert_jpeg(img.content)


async def test_private_member_share_returns_generic_404(
    client, make_admin, fetch_csrf, monkeypatch, public_frontend_url
):
    _member_client, _token, readable = await _setup_member(
        client, make_admin, fetch_csrf, monkeypatch,
        email="shareprivate@example.com", visibility="private",
    )

    res = await client.get(f"/share/members/{readable}")
    assert res.status_code == 404
    assert "noindex, nofollow" in res.text
    assert readable not in res.text

    img = await client.get(f"/share/members/{readable}/image")
    assert img.status_code == 404


async def test_project_share_document_and_image(
    client, make_admin, fetch_csrf, public_frontend_url
):
    token = await login_admin(client, make_admin, fetch_csrf)
    published = await create_project(
        client, token, name="Aurora Platform", status="published"
    )
    await create_project(client, token, name="Hidden Draft", status="draft")

    res = await client.get(f"/share/projects/{published['slug']}")
    assert res.status_code == 200, res.text
    canonical = f"{_PUBLIC_URL}/projects/{published['slug']}"
    image = f"{_PUBLIC_URL}/share/projects/{published['slug']}/image"
    _assert_meta(res.text, canonical, image)

    img = await client.get(f"/share/projects/{published['slug']}/image")
    assert img.status_code == 200
    _assert_jpeg(img.content)

    draft = await client.get("/share/projects/hidden-draft")
    assert draft.status_code == 404
    assert "noindex, nofollow" in draft.text


async def test_work_share_respects_public_visibility(
    client, make_admin, fetch_csrf, monkeypatch, public_frontend_url
):
    member_client, token, readable = await _setup_member(
        client, make_admin, fetch_csrf, monkeypatch,
        email="sharework@example.com", visibility="public",
    )

    public_work = await create_work(member_client, token, title="Public Showcase")
    await publish_work(member_client, token, public_work["id"])
    await patch_work(member_client, token, public_work["id"], visibility="public")

    res = await client.get(f"/share/members/{readable}/works/{public_work['slug']}")
    assert res.status_code == 200, res.text
    canonical = f"{_PUBLIC_URL}/members/{readable}/works/{public_work['slug']}"
    image = f"{_PUBLIC_URL}/share/members/{readable}/works/{public_work['slug']}/image"
    _assert_meta(res.text, canonical, image)

    img = await client.get(
        f"/share/members/{readable}/works/{public_work['slug']}/image"
    )
    assert img.status_code == 200
    _assert_jpeg(img.content)

    # Published but visibility=private → not shareable.
    private_work = await create_work(member_client, token, title="Private Piece")
    await publish_work(member_client, token, private_work["id"])
    hidden = await client.get(
        f"/share/members/{readable}/works/{private_work['slug']}"
    )
    assert hidden.status_code == 404


async def test_work_share_404_for_private_member(
    client, make_admin, fetch_csrf, monkeypatch, public_frontend_url
):
    member_client, token, readable = await _setup_member(
        client, make_admin, fetch_csrf, monkeypatch,
        email="shareprivwork@example.com", visibility="private",
    )
    work = await create_work(member_client, token, title="Should Not Share", visibility="public")
    await publish_work(member_client, token, work["id"])

    res = await client.get(f"/share/members/{readable}/works/{work['slug']}")
    assert res.status_code == 404
    assert "noindex, nofollow" in res.text
