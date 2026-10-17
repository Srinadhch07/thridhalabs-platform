"""Lab Member Account System tests (Phase 9).

Covers admin provisioning/lifecycle, onboarding token single-use semantics,
member login/logout, profile completion, password change, profile pictures and
the strict isolation between member sessions and admin sessions.
"""

from __future__ import annotations

import re

from httpx import ASGITransport, AsyncClient

from app.core.config import get_settings
from app.main import app
from app.models.admin import Role
from tests._content_helpers import (
    MEMBER_PASSWORD,
    capture_onboarding_token,
    complete_member_profile,
    create_member,
    create_opportunity,
    login_admin,
    member_login,
    member_setup,
    png_bytes,
)

MEMBER_ID_RE = re.compile(r"^THL-M-\d{4}-\d{4}$")
ADMIN_PASSWORD = "CorrectHorse!Battery9"


async def relogin_admin(client, fetch_csrf, email: str = "owner@example.com") -> str:
    """Log the (already-created) admin back in and return a fresh CSRF token."""
    token = await fetch_csrf()
    res = await client.post(
        "/api/auth/login",
        json={"email": email, "password": ADMIN_PASSWORD},
        headers={"X-CSRF-Token": token},
    )
    assert res.status_code == 200, res.text
    return await fetch_csrf()


async def _member_csrf(client) -> str:
    res = await client.get("/api/member/csrf")
    assert res.status_code == 200, res.text
    return res.json()["csrfToken"]


def _second_client() -> AsyncClient:
    """An independent cookie jar over the already-running app (used to hold a
    member session while the primary client holds an admin session)."""
    return AsyncClient(transport=ASGITransport(app=app), base_url="https://testserver")


# ---------------------------------------------------------------------------
# Admin provisioning
# ---------------------------------------------------------------------------
async def test_create_member_returns_readable_id(client, make_admin, fetch_csrf, monkeypatch):
    capture = capture_onboarding_token(monkeypatch)
    token = await login_admin(client, make_admin, fetch_csrf)

    member = await create_member(
        client, token, email="Alice@Example.com", full_name="Alice"
    )
    assert MEMBER_ID_RE.match(member["member_id"]), member["member_id"]
    assert member["email"] == "alice@example.com"  # normalized
    assert member["status"] == "pending_setup"
    assert member["onboarding_sent"] is True
    assert member["profile_complete"] is False
    assert capture["token"], "an onboarding email should have been sent"

    # No secrets ever cross the API boundary.
    assert "password_hash" not in member
    assert "onboarding" not in member
    assert "token" not in str(member)


async def test_create_member_duplicate_email_conflicts(client, make_admin, fetch_csrf, monkeypatch):
    capture_onboarding_token(monkeypatch)
    token = await login_admin(client, make_admin, fetch_csrf)
    await create_member(client, token, email="dup@example.com")

    res = await client.post(
        "/api/members", json={"email": "DUP@example.com"}, headers={"X-CSRF-Token": token}
    )
    assert res.status_code == 409, res.text
    assert res.json()["error"]["code"] == "EMAIL_TAKEN"


async def test_create_member_invalid_opportunity_rejected(client, make_admin, fetch_csrf, monkeypatch):
    capture_onboarding_token(monkeypatch)
    token = await login_admin(client, make_admin, fetch_csrf)
    res = await client.post(
        "/api/members",
        json={"email": "x@example.com", "joined_opportunity_id": "not-an-objectid"},
        headers={"X-CSRF-Token": token},
    )
    assert res.status_code == 400, res.text
    assert res.json()["error"]["code"] == "INVALID_OPPORTUNITY"


async def test_create_member_with_valid_opportunity(client, make_admin, fetch_csrf, monkeypatch):
    capture_onboarding_token(monkeypatch)
    token = await login_admin(client, make_admin, fetch_csrf)
    opp = await create_opportunity(client, token)
    member = await create_member(
        client, token, email="linked@example.com", joined_opportunity_id=opp["id"]
    )
    assert member["joined_opportunity_id"] == opp["id"]


async def test_create_member_requires_csrf(client, make_admin, fetch_csrf, monkeypatch):
    capture_onboarding_token(monkeypatch)
    await login_admin(client, make_admin, fetch_csrf)
    res = await client.post("/api/members", json={"email": "nocsrf@example.com"})
    assert res.status_code == 403


async def test_create_member_requires_admin_role(client, make_admin, fetch_csrf, monkeypatch):
    capture_onboarding_token(monkeypatch)
    editor = await login_admin(
        client, make_admin, fetch_csrf, email="editor@example.com", role=Role.EDITOR
    )
    res = await client.post(
        "/api/members", json={"email": "e@example.com"}, headers={"X-CSRF-Token": editor}
    )
    assert res.status_code == 403


# ---------------------------------------------------------------------------
# Admin listing / retrieval / update
# ---------------------------------------------------------------------------
async def test_list_members_requires_admin(client, make_admin, fetch_csrf, monkeypatch):
    capture_onboarding_token(monkeypatch)
    assert (await client.get("/api/members")).status_code == 401

    editor = await login_admin(
        client, make_admin, fetch_csrf, email="editor@example.com", role=Role.EDITOR
    )
    res = await client.get("/api/members")
    assert res.status_code == 403


async def test_list_members_pagination_and_filters(client, make_admin, fetch_csrf, monkeypatch):
    capture_onboarding_token(monkeypatch)
    token = await login_admin(client, make_admin, fetch_csrf)
    for name in ("anna", "ben", "cara"):
        await create_member(client, token, email=f"{name}@example.com", full_name=name.title())

    page1 = await client.get("/api/members?page=1&page_size=2", headers={"X-CSRF-Token": token})
    assert page1.status_code == 200, page1.text
    body = page1.json()
    assert body["total"] == 3
    assert body["pages"] == 2
    assert len(body["items"]) == 2

    searched = await client.get("/api/members?search=ben", headers={"X-CSRF-Token": token})
    assert searched.json()["total"] == 1
    assert searched.json()["items"][0]["email"] == "ben@example.com"

    pending = await client.get("/api/members?status=pending_setup", headers={"X-CSRF-Token": token})
    assert pending.json()["total"] == 3

    active = await client.get("/api/members?status=active", headers={"X-CSRF-Token": token})
    assert active.json()["total"] == 0

    bad_sort = await client.get("/api/members?sort=bogus", headers={"X-CSRF-Token": token})
    assert bad_sort.status_code == 422


async def test_list_members_search_covers_role_label(client, make_admin, fetch_csrf, monkeypatch):
    """Search matches the member's role/designation (case-insensitive, partial)."""
    capture_onboarding_token(monkeypatch)
    token = await login_admin(client, make_admin, fetch_csrf)
    await create_member(
        client,
        token,
        email="ada@example.com",
        full_name="Ada Lovelace",
        role_label="AI Engineer",
    )
    await create_member(
        client,
        token,
        email="grace@example.com",
        full_name="Grace Hopper",
        role_label="Frontend Developer",
    )

    res = await client.get("/api/members?search=engineer", headers={"X-CSRF-Token": token})
    assert res.status_code == 200, res.text
    body = res.json()
    assert body["total"] == 1
    assert body["items"][0]["email"] == "ada@example.com"

    frontend = await client.get("/api/members?search=front", headers={"X-CSRF-Token": token})
    assert frontend.json()["total"] == 1
    assert frontend.json()["items"][0]["role_label"] == "Frontend Developer"


async def test_get_member_and_not_found(client, make_admin, fetch_csrf, monkeypatch):
    capture_onboarding_token(monkeypatch)
    token = await login_admin(client, make_admin, fetch_csrf)
    member = await create_member(client, token, email="get@example.com")

    res = await client.get(f"/api/members/{member['id']}", headers={"X-CSRF-Token": token})
    assert res.status_code == 200, res.text
    assert res.json()["member_id"] == member["member_id"]

    missing = await client.get("/api/members/64b7f0000000000000000000", headers={"X-CSRF-Token": token})
    assert missing.status_code == 404

    invalid = await client.get("/api/members/not-an-id", headers={"X-CSRF-Token": token})
    assert invalid.status_code == 404


async def test_update_member_fields(client, make_admin, fetch_csrf, monkeypatch):
    capture_onboarding_token(monkeypatch)
    token = await login_admin(client, make_admin, fetch_csrf)
    member = await create_member(client, token, email="patch@example.com")

    res = await client.patch(
        f"/api/members/{member['id']}",
        json={"role_label": "Research Lead", "internal_note": "Strong candidate."},
        headers={"X-CSRF-Token": token},
    )
    assert res.status_code == 200, res.text
    body = res.json()
    assert body["role_label"] == "Research Lead"
    assert body["internal_note"] == "Strong candidate."


async def test_update_member_duplicate_email_conflict(client, make_admin, fetch_csrf, monkeypatch):
    capture_onboarding_token(monkeypatch)
    token = await login_admin(client, make_admin, fetch_csrf)
    await create_member(client, token, email="one@example.com")
    two = await create_member(client, token, email="two@example.com")

    res = await client.patch(
        f"/api/members/{two['id']}",
        json={"email": "one@example.com"},
        headers={"X-CSRF-Token": token},
    )
    assert res.status_code == 409, res.text
    assert res.json()["error"]["code"] == "EMAIL_TAKEN"


# ---------------------------------------------------------------------------
# Onboarding token lifecycle
# ---------------------------------------------------------------------------
async def test_setup_completes_and_clears_token(client, make_admin, fetch_csrf, monkeypatch):
    capture = capture_onboarding_token(monkeypatch)
    token = await login_admin(client, make_admin, fetch_csrf)
    await create_member(client, token, email="setup@example.com", full_name="Setup Person")

    await member_setup(client, capture["token"])

    # Single-use: replaying the same link fails.
    replay = await client.post(
        "/api/member/setup",
        json={"token": capture["token"], "password": MEMBER_PASSWORD},
        headers={"X-CSRF-Token": await _member_csrf(client)},
    )
    assert replay.status_code == 400
    assert replay.json()["error"]["code"] == "INVALID_ONBOARDING_TOKEN"

    await member_login(client, "setup@example.com")
    me = await client.get("/api/member/me")
    assert me.status_code == 200
    assert me.json()["status"] == "pending_setup"  # profile not yet completed


async def test_setup_invalid_token_rejected(client):
    res = await client.post(
        "/api/member/setup",
        json={"token": "totally-invalid-token-value", "password": MEMBER_PASSWORD},
        headers={"X-CSRF-Token": await _member_csrf(client)},
    )
    assert res.status_code == 400
    assert res.json()["error"]["code"] == "INVALID_ONBOARDING_TOKEN"


async def test_setup_weak_password_rejected(client, make_admin, fetch_csrf, monkeypatch):
    capture = capture_onboarding_token(monkeypatch)
    token = await login_admin(client, make_admin, fetch_csrf)
    await create_member(client, token, email="weak@example.com")

    res = await client.post(
        "/api/member/setup",
        json={"token": capture["token"], "password": "short"},
        headers={"X-CSRF-Token": await _member_csrf(client)},
    )
    assert res.status_code == 400
    assert res.json()["error"]["code"] == "WEAK_PASSWORD"


async def test_setup_rate_limited(client):
    settings = get_settings()
    for _ in range(settings.LOGIN_RATE_LIMIT_MAX):
        res = await client.post(
            "/api/member/setup",
            json={"token": "bad-token-attempt-value", "password": MEMBER_PASSWORD},
            headers={"X-CSRF-Token": await _member_csrf(client)},
        )
        assert res.status_code == 400

    blocked = await client.post(
        "/api/member/setup",
        json={"token": "bad-token-attempt-value", "password": MEMBER_PASSWORD},
        headers={"X-CSRF-Token": await _member_csrf(client)},
    )
    assert blocked.status_code == 429
    assert blocked.json()["error"]["code"] == "RATE_LIMITED"


async def test_resend_invalidates_old_token(client, make_admin, fetch_csrf, monkeypatch):
    capture = capture_onboarding_token(monkeypatch)
    token = await login_admin(client, make_admin, fetch_csrf)
    member = await create_member(client, token, email="resend@example.com")
    first = capture["token"]

    res = await client.post(
        f"/api/members/{member['id']}/resend", headers={"X-CSRF-Token": token}
    )
    assert res.status_code == 200, res.text
    second = capture["token"]
    assert second and second != first

    stale = await client.post(
        "/api/member/setup",
        json={"token": first, "password": MEMBER_PASSWORD},
        headers={"X-CSRF-Token": await _member_csrf(client)},
    )
    assert stale.status_code == 400

    await member_setup(client, second)


async def test_resend_rejected_after_completion(client, make_admin, fetch_csrf, monkeypatch):
    capture = capture_onboarding_token(monkeypatch)
    token = await login_admin(client, make_admin, fetch_csrf)
    member = await create_member(client, token, email="done@example.com")
    await member_setup(client, capture["token"])

    token = await fetch_csrf()
    res = await client.post(
        f"/api/members/{member['id']}/resend", headers={"X-CSRF-Token": token}
    )
    assert res.status_code == 409
    assert res.json()["error"]["code"] == "ONBOARDING_ALREADY_COMPLETE"


# ---------------------------------------------------------------------------
# Member session (login / logout / isolation)
# ---------------------------------------------------------------------------
async def test_member_login_and_me(client, make_admin, fetch_csrf, monkeypatch):
    capture = capture_onboarding_token(monkeypatch)
    token = await login_admin(client, make_admin, fetch_csrf)
    member = await create_member(client, token, email="login@example.com", full_name="Login Person")
    await member_setup(client, capture["token"])

    await member_login(client, "login@example.com")
    me = await client.get("/api/member/me")
    assert me.status_code == 200, me.text
    body = me.json()
    assert body["member_id"] == member["member_id"]
    assert body["email"] == "login@example.com"
    assert body["full_name"] == "Login Person"
    assert "internal_note" not in body
    assert "password_hash" not in body


async def test_member_login_bad_password_and_unknown_email(client, make_admin, fetch_csrf, monkeypatch):
    capture = capture_onboarding_token(monkeypatch)
    token = await login_admin(client, make_admin, fetch_csrf)
    await create_member(client, token, email="known@example.com")
    await member_setup(client, capture["token"])

    csrf = await _member_csrf(client)
    wrong = await client.post(
        "/api/member/login",
        json={"email": "known@example.com", "password": "WrongPass!123"},
        headers={"X-CSRF-Token": csrf},
    )
    assert wrong.status_code == 401
    assert wrong.json()["error"]["code"] == "INVALID_CREDENTIALS"

    unknown = await client.post(
        "/api/member/login",
        json={"email": "nobody@example.com", "password": MEMBER_PASSWORD},
        headers={"X-CSRF-Token": csrf},
    )
    assert unknown.status_code == 401


async def test_member_login_rate_limited(client, make_admin, fetch_csrf, monkeypatch):
    settings = get_settings()
    capture = capture_onboarding_token(monkeypatch)
    token = await login_admin(client, make_admin, fetch_csrf)
    await create_member(client, token, email="limited-member@example.com")
    await member_setup(client, capture["token"])

    for _ in range(settings.LOGIN_RATE_LIMIT_MAX):
        res = await client.post(
            "/api/member/login",
            json={"email": "limited-member@example.com", "password": "WrongPass!123"},
            headers={"X-CSRF-Token": await _member_csrf(client)},
        )
        assert res.status_code == 401

    blocked = await client.post(
        "/api/member/login",
        json={"email": "limited-member@example.com", "password": MEMBER_PASSWORD},
        headers={"X-CSRF-Token": await _member_csrf(client)},
    )
    assert blocked.status_code == 429


async def test_member_logout_revokes_session(client, make_admin, fetch_csrf, monkeypatch):
    capture = capture_onboarding_token(monkeypatch)
    token = await login_admin(client, make_admin, fetch_csrf)
    await create_member(client, token, email="logout@example.com")
    await member_setup(client, capture["token"])

    csrf = await member_login(client, "logout@example.com")
    assert (await client.get("/api/member/me")).status_code == 200

    out = await client.post("/api/member/logout", headers={"X-CSRF-Token": csrf})
    assert out.status_code == 200, out.text
    assert (await client.get("/api/member/me")).status_code == 401


async def test_member_and_admin_sessions_are_isolated(client, make_admin, fetch_csrf, monkeypatch):
    capture = capture_onboarding_token(monkeypatch)
    token = await login_admin(client, make_admin, fetch_csrf)
    await create_member(client, token, email="iso@example.com")
    await member_setup(client, capture["token"])

    # A member session alone (its own cookie jar) cannot reach admin endpoints,
    # even though the member token is a valid JWT — it carries typ=member.
    async with _second_client() as member_client:
        await member_login(member_client, "iso@example.com")
        assert (await member_client.get("/api/member/me")).status_code == 200
        assert (await member_client.get("/api/members")).status_code == 401
        assert (await member_client.get("/api/auth/me")).status_code == 401

    # An admin session alone cannot reach member endpoints.
    async with _second_client() as admin_client:
        csrf = (await admin_client.get("/api/auth/csrf")).json()["csrfToken"]
        res = await admin_client.post(
            "/api/auth/login",
            json={"email": "owner@example.com", "password": ADMIN_PASSWORD},
            headers={"X-CSRF-Token": csrf},
        )
        assert res.status_code == 200, res.text
        assert (await admin_client.get("/api/auth/me")).status_code == 200
        assert (await admin_client.get("/api/member/me")).status_code == 401


# ---------------------------------------------------------------------------
# Profile
# ---------------------------------------------------------------------------
async def test_profile_completion_activates_member(client, make_admin, fetch_csrf, monkeypatch):
    capture = capture_onboarding_token(monkeypatch)
    token = await login_admin(client, make_admin, fetch_csrf)
    await create_member(client, token, email="active@example.com", full_name="Active Person")
    await member_setup(client, capture["token"])
    await member_login(client, "active@example.com")

    profile = await complete_member_profile(client, await _member_csrf(client))
    assert profile["status"] == "active"
    assert profile["profile_complete"] is True
    assert profile["profile"]["completed_at"] is not None

    assert (await client.get("/api/member/me")).json()["status"] == "active"


async def test_profile_incomplete_without_full_name_stays_pending(client, make_admin, fetch_csrf, monkeypatch):
    capture = capture_onboarding_token(monkeypatch)
    token = await login_admin(client, make_admin, fetch_csrf)
    await create_member(client, token, email="noname@example.com")  # no full_name
    await member_setup(client, capture["token"])
    await member_login(client, "noname@example.com")

    profile = await complete_member_profile(client, await _member_csrf(client))
    assert profile["status"] == "pending_setup"
    assert profile["profile_complete"] is False


async def test_profile_validation_rules(client, make_admin, fetch_csrf, monkeypatch):
    capture = capture_onboarding_token(monkeypatch)
    token = await login_admin(client, make_admin, fetch_csrf)
    await create_member(client, token, email="validation@example.com", full_name="Val Person")
    await member_setup(client, capture["token"])
    await member_login(client, "validation@example.com")
    csrf = await _member_csrf(client)

    bad_tz = await client.patch(
        "/api/member/profile",
        json={"bio": "x", "skills": ["a"], "interests": ["b"], "timezone": "Not/AZone"},
        headers={"X-CSRF-Token": csrf},
    )
    assert bad_tz.status_code == 422

    bad_url = await client.patch(
        "/api/member/profile",
        json={"bio": "x", "skills": ["a"], "interests": ["b"], "github_url": "javascript:alert(1)"},
        headers={"X-CSRF-Token": csrf},
    )
    assert bad_url.status_code == 422

    too_many = await client.patch(
        "/api/member/profile",
        json={"bio": "x", "skills": [f"t{i}" for i in range(100)], "interests": []},
        headers={"X-CSRF-Token": csrf},
    )
    assert too_many.status_code == 422


async def test_profile_patch_requires_csrf(client, make_admin, fetch_csrf, monkeypatch):
    capture = capture_onboarding_token(monkeypatch)
    token = await login_admin(client, make_admin, fetch_csrf)
    await create_member(client, token, email="csrfp@example.com", full_name="CSRF P")
    await member_setup(client, capture["token"])
    await member_login(client, "csrfp@example.com")

    res = await client.patch(
        "/api/member/profile", json={"bio": "x", "skills": [], "interests": []}
    )
    assert res.status_code == 403


# ---------------------------------------------------------------------------
# Password change
# ---------------------------------------------------------------------------
async def test_password_change_flow(client, make_admin, fetch_csrf, monkeypatch):
    capture = capture_onboarding_token(monkeypatch)
    token = await login_admin(client, make_admin, fetch_csrf)
    await create_member(client, token, email="pw@example.com", full_name="PW Person")
    await member_setup(client, capture["token"])
    csrf = await member_login(client, "pw@example.com")

    wrong = await client.post(
        "/api/member/password",
        json={"current_password": "WrongPass!123", "new_password": "BrandNewPass!9"},
        headers={"X-CSRF-Token": csrf},
    )
    assert wrong.status_code == 401

    same = await client.post(
        "/api/member/password",
        json={"current_password": MEMBER_PASSWORD, "new_password": MEMBER_PASSWORD},
        headers={"X-CSRF-Token": csrf},
    )
    assert same.status_code == 400

    ok = await client.post(
        "/api/member/password",
        json={"current_password": MEMBER_PASSWORD, "new_password": "BrandNewPass!9"},
        headers={"X-CSRF-Token": csrf},
    )
    assert ok.status_code == 200, ok.text

    # Old password no longer works; the new one does.
    async def _attempt(password: str) -> int:
        res = await client.post(
            "/api/member/login",
            json={"email": "pw@example.com", "password": password},
            headers={"X-CSRF-Token": await _member_csrf(client)},
        )
        return res.status_code

    assert await _attempt(MEMBER_PASSWORD) == 401
    assert await _attempt("BrandNewPass!9") == 200


# ---------------------------------------------------------------------------
# Profile picture
# ---------------------------------------------------------------------------
async def test_profile_picture_upload_and_clear(client, make_admin, fetch_csrf, monkeypatch):
    capture = capture_onboarding_token(monkeypatch)
    token = await login_admin(client, make_admin, fetch_csrf)
    await create_member(client, token, email="pic@example.com", full_name="Pic Person")
    await member_setup(client, capture["token"])
    await member_login(client, "pic@example.com")

    me = (await client.get("/api/member/me")).json()
    csrf = await _member_csrf(client)
    upload = await client.post(
        "/api/member/picture",
        files={"file": ("avatar.png", png_bytes(40, 40, "purple"), "image/png")},
        headers={"X-CSRF-Token": csrf},
    )
    assert upload.status_code == 200, upload.text
    media = upload.json()
    assert media["created_by"] == me["id"]

    profile = await client.get("/api/member/profile")
    assert profile.json()["profile"]["picture_media_id"] == media["id"]

    cleared = await client.delete("/api/member/picture", headers={"X-CSRF-Token": csrf})
    assert cleared.status_code == 200, cleared.text
    assert cleared.json()["profile"]["picture_media_id"] is None

    # The owned media document was removed with the association.
    gone = await client.get(f"/api/public/media/{media['id']}")
    assert gone.status_code == 404


async def test_picture_rejects_media_owned_by_another(client, make_admin, fetch_csrf, monkeypatch):
    capture = capture_onboarding_token(monkeypatch)
    token = await login_admin(client, make_admin, fetch_csrf)
    # Admin uploads an image first (admins are the media owners here).
    shared = png_bytes(48, 32, "orange")
    admin_upload = await client.post(
        "/api/media",
        files={"file": ("shared.png", shared, "image/png")},
        headers={"X-CSRF-Token": token},
    )
    assert admin_upload.status_code == 201, admin_upload.text
    admin_media_id = admin_upload.json()["id"]

    await create_member(client, token, email="borrower@example.com", full_name="Borrower")
    await member_setup(client, capture["token"])
    await member_login(client, "borrower@example.com")

    res = await client.post(
        "/api/member/picture",
        files={"file": ("shared.png", shared, "image/png")},
        headers={"X-CSRF-Token": await _member_csrf(client)},
    )
    assert res.status_code == 409, res.text
    assert res.json()["error"]["code"] == "MEDIA_NOT_OWNED"

    # The member did not silently adopt the admin's media.
    assert (await client.get("/api/member/profile")).json()["profile"]["picture_media_id"] is None
    assert (await client.get(f"/api/public/media/{admin_media_id}")).status_code == 200


# ---------------------------------------------------------------------------
# Deactivate / reactivate / delete
# ---------------------------------------------------------------------------
async def test_deactivate_revokes_session_and_blocks_login(client, make_admin, fetch_csrf, monkeypatch):
    capture = capture_onboarding_token(monkeypatch)
    token = await login_admin(client, make_admin, fetch_csrf)
    member = await create_member(client, token, email="deact@example.com", full_name="Deact Person")
    await member_setup(client, capture["token"])

    # Hold the member session on a second client so the admin session on the
    # primary client does not overwrite the (shared-name) session cookie.
    async with _second_client() as member_client:
        await member_login(member_client, "deact@example.com")
        assert (await member_client.get("/api/member/me")).status_code == 200

        admin_token = await fetch_csrf()
        deactivated = await client.post(
            f"/api/members/{member['id']}/deactivate",
            headers={"X-CSRF-Token": admin_token},
        )
        assert deactivated.status_code == 200, deactivated.text
        assert deactivated.json()["status"] == "inactive"

        # The pre-existing member session is revoked (token_version bumped).
        assert (await member_client.get("/api/member/me")).status_code == 401

        # A fresh login is refused outright.
        blocked = await member_client.post(
            "/api/member/login",
            json={"email": "deact@example.com", "password": MEMBER_PASSWORD},
            headers={"X-CSRF-Token": await _member_csrf(member_client)},
        )
        assert blocked.status_code == 403
        assert blocked.json()["error"]["code"] == "ACCOUNT_DISABLED"


async def test_reactivate_restores_login(client, make_admin, fetch_csrf, monkeypatch):
    capture = capture_onboarding_token(monkeypatch)
    token = await login_admin(client, make_admin, fetch_csrf)
    member = await create_member(client, token, email="react@example.com", full_name="React Person")
    await member_setup(client, capture["token"])
    csrf = await member_login(client, "react@example.com")
    await complete_member_profile(client, csrf)

    admin_token = await relogin_admin(client, fetch_csrf)
    await client.post(f"/api/members/{member['id']}/deactivate", headers={"X-CSRF-Token": admin_token})
    reactivated = await client.post(
        f"/api/members/{member['id']}/reactivate", headers={"X-CSRF-Token": admin_token}
    )
    assert reactivated.status_code == 200, reactivated.text
    assert reactivated.json()["status"] == "active"

    await member_login(client, "react@example.com")
    assert (await client.get("/api/member/me")).status_code == 200


async def test_reactivate_never_onboarded_reissues_link(client, make_admin, fetch_csrf, monkeypatch):
    capture = capture_onboarding_token(monkeypatch)
    token = await login_admin(client, make_admin, fetch_csrf)
    member = await create_member(client, token, email="pdf@example.com")

    admin_token = token
    await client.post(f"/api/members/{member['id']}/deactivate", headers={"X-CSRF-Token": admin_token})
    refreshed = await client.post(
        f"/api/members/{member['id']}/reactivate", headers={"X-CSRF-Token": admin_token}
    )
    assert refreshed.status_code == 200, refreshed.text
    assert refreshed.json()["status"] == "pending_setup"
    assert refreshed.json()["onboarding_sent"] is True
    assert capture["token"]

    await member_setup(client, capture["token"])


async def test_delete_requires_owner(client, make_admin, fetch_csrf, monkeypatch):
    capture_onboarding_token(monkeypatch)
    token = await login_admin(client, make_admin, fetch_csrf)
    member = await create_member(client, token, email="del@example.com")

    admin_token = await login_admin(
        client, make_admin, fetch_csrf, email="admin2@example.com", role=Role.ADMIN
    )
    forbidden = await client.delete(
        f"/api/members/{member['id']}", headers={"X-CSRF-Token": admin_token}
    )
    assert forbidden.status_code == 403

    owner_token = await login_admin(
        client, make_admin, fetch_csrf, email="owner2@example.com", role=Role.OWNER
    )
    deleted = await client.delete(
        f"/api/members/{member['id']}", headers={"X-CSRF-Token": owner_token}
    )
    assert deleted.status_code == 200, deleted.text
    assert (await client.get(f"/api/members/{member['id']}")).status_code == 404


async def test_member_id_is_sequential_and_never_reused(client, make_admin, fetch_csrf, monkeypatch):
    capture_onboarding_token(monkeypatch)
    token = await login_admin(client, make_admin, fetch_csrf)
    first = await create_member(client, token, email="seq1@example.com")
    second = await create_member(client, token, email="seq2@example.com")

    suffix1 = int(first["member_id"].rsplit("-", 1)[1])
    suffix2 = int(second["member_id"].rsplit("-", 1)[1])
    assert suffix2 == suffix1 + 1

    owner_token = await login_admin(
        client, make_admin, fetch_csrf, email="owner3@example.com", role=Role.OWNER
    )
    await client.delete(f"/api/members/{first['id']}", headers={"X-CSRF-Token": owner_token})

    # Re-authenticate as the original admin, then create another member. The
    # counter must advance — the deleted id is never handed out again.
    token = await relogin_admin(client, fetch_csrf, "owner@example.com")
    third = await create_member(client, token, email="seq3@example.com")
    suffix3 = int(third["member_id"].rsplit("-", 1)[1])
    assert suffix3 == suffix2 + 1, "deleted member ids must never be reused"


async def test_deactivate_clears_pending_setup_link(client, make_admin, fetch_csrf, monkeypatch):
    capture = capture_onboarding_token(monkeypatch)
    token = await login_admin(client, make_admin, fetch_csrf)
    member = await create_member(client, token, email="clearlink@example.com")
    setup_token = capture["token"]

    await client.post(f"/api/members/{member['id']}/deactivate", headers={"X-CSRF-Token": token})
    res = await client.post(
        "/api/member/setup",
        json={"token": setup_token, "password": MEMBER_PASSWORD},
        headers={"X-CSRF-Token": await _member_csrf(client)},
    )
    assert res.status_code == 400