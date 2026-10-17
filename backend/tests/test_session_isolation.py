"""Admin vs Lab Member session independence.

Before the fix both portals shared one session cookie + one CSRF cookie, so the
second sign-in overwrote the first. These tests pin the new contract: each realm
owns dedicated cookies and can hold a live session in the *same* browser
(single cookie jar), with independent logout and non-interchangeable CSRF.
"""

from __future__ import annotations

from httpx import ASGITransport, AsyncClient

from app.core.config import get_settings
from app.main import app
from tests._content_helpers import (
    MEMBER_PASSWORD,
    capture_onboarding_token,
    create_member,
    login_admin,
    member_login,
    member_setup,
)

ADMIN_PASSWORD = "CorrectHorse!Battery9"


def _second_client(cookies: dict[str, str] | None = None) -> AsyncClient:
    return AsyncClient(
        transport=ASGITransport(app=app),
        base_url="https://testserver",
        cookies=cookies,
    )


async def _admin_login(client, email: str = "owner@example.com") -> str:
    csrf = (await client.get("/api/auth/csrf")).json()["csrfToken"]
    res = await client.post(
        "/api/auth/login",
        json={"email": email, "password": ADMIN_PASSWORD},
        headers={"X-CSRF-Token": csrf},
    )
    assert res.status_code == 200, res.text
    return (await client.get("/api/auth/csrf")).json()["csrfToken"]


async def _member_csrf(client) -> str:
    res = await client.get("/api/member/csrf")
    assert res.status_code == 200, res.text
    return res.json()["csrfToken"]


async def _admin_logout(client):
    csrf = (await client.get("/api/auth/csrf")).json()["csrfToken"]
    res = await client.post("/api/auth/logout", headers={"X-CSRF-Token": csrf})
    assert res.status_code == 200, res.text
    return res


async def _provision_member(client, make_admin, fetch_csrf, monkeypatch, email="coexist@example.com"):
    """Admin is logged in on `client`; the member is created + onboarded."""
    capture = capture_onboarding_token(monkeypatch)
    token = await login_admin(client, make_admin, fetch_csrf)
    member = await create_member(client, token, email=email)
    await member_setup(client, capture["token"])
    return member


# ---------------------------------------------------------------------------
# Coexistence in one cookie jar
# ---------------------------------------------------------------------------
async def test_admin_then_member_sessions_coexist(client, make_admin, fetch_csrf, monkeypatch):
    await _provision_member(client, make_admin, fetch_csrf, monkeypatch)
    # Member signs in on the same jar that already holds the Admin session.
    await member_login(client, "coexist@example.com")

    assert (await client.get("/api/auth/me")).status_code == 200
    assert (await client.get("/api/member/me")).status_code == 200


async def test_member_then_admin_sessions_coexist(client, make_admin, fetch_csrf, monkeypatch):
    await _provision_member(client, make_admin, fetch_csrf, monkeypatch)

    # Establish the member session first, with no Admin session present.
    await _admin_logout(client)
    await member_login(client, "coexist@example.com")
    assert (await client.get("/api/member/me")).status_code == 200
    assert (await client.get("/api/auth/me")).status_code == 401

    # Admin signs in afterwards; the member session survives.
    await _admin_login(client)
    assert (await client.get("/api/auth/me")).status_code == 200
    assert (await client.get("/api/member/me")).status_code == 200


# ---------------------------------------------------------------------------
# Independent logout
# ---------------------------------------------------------------------------
async def test_admin_logout_leaves_member_session(client, make_admin, fetch_csrf, monkeypatch):
    await _provision_member(client, make_admin, fetch_csrf, monkeypatch)
    await member_login(client, "coexist@example.com")

    await _admin_logout(client)

    assert (await client.get("/api/auth/me")).status_code == 401
    assert (await client.get("/api/member/me")).status_code == 200


async def test_member_logout_leaves_admin_session(client, make_admin, fetch_csrf, monkeypatch):
    await _provision_member(client, make_admin, fetch_csrf, monkeypatch)
    await member_login(client, "coexist@example.com")

    csrf = await _member_csrf(client)
    out = await client.post("/api/member/logout", headers={"X-CSRF-Token": csrf})
    assert out.status_code == 200, out.text

    assert (await client.get("/api/member/me")).status_code == 401
    assert (await client.get("/api/auth/me")).status_code == 200


async def test_admin_logout_deletes_only_admin_cookies(client, make_admin, fetch_csrf, monkeypatch):
    settings = get_settings()
    await _provision_member(client, make_admin, fetch_csrf, monkeypatch)
    await member_login(client, "coexist@example.com")

    res = await _admin_logout(client)
    cookies = " ".join(res.headers.get_list("set-cookie"))

    assert f"{settings.COOKIE_NAME}=" in cookies
    assert f"{settings.CSRF_COOKIE_NAME}=" in cookies
    assert f"{settings.MEMBER_COOKIE_NAME}=" not in cookies
    assert f"{settings.MEMBER_CSRF_COOKIE_NAME}=" not in cookies


async def test_member_logout_deletes_only_member_cookies(client, make_admin, fetch_csrf, monkeypatch):
    settings = get_settings()
    await _provision_member(client, make_admin, fetch_csrf, monkeypatch)
    await member_login(client, "coexist@example.com")

    res = await client.post(
        "/api/member/logout", headers={"X-CSRF-Token": await _member_csrf(client)}
    )
    cookies = " ".join(res.headers.get_list("set-cookie"))

    assert f"{settings.MEMBER_COOKIE_NAME}=" in cookies
    assert f"{settings.MEMBER_CSRF_COOKIE_NAME}=" in cookies
    assert f"{settings.COOKIE_NAME}=" not in cookies
    assert f"{settings.CSRF_COOKIE_NAME}=" not in cookies


# ---------------------------------------------------------------------------
# CSRF is per-realm
# ---------------------------------------------------------------------------
async def test_realm_csrf_tokens_are_not_interchangeable(client, make_admin, fetch_csrf, monkeypatch):
    await _provision_member(client, make_admin, fetch_csrf, monkeypatch)
    await member_login(client, "coexist@example.com")

    admin_csrf = (await client.get("/api/auth/csrf")).json()["csrfToken"]
    member_csrf = await _member_csrf(client)

    # Admin mutation accepts the Admin token, rejects the Member token.
    ok = await client.post(
        "/api/clients", json={"name": "Acme"}, headers={"X-CSRF-Token": admin_csrf}
    )
    assert ok.status_code == 201, ok.text

    bad = await client.post(
        "/api/clients", json={"name": "Beta"}, headers={"X-CSRF-Token": member_csrf}
    )
    assert bad.status_code == 403
    assert bad.json()["error"]["code"] == "CSRF_INVALID"

    # Member mutation accepts the Member token, rejects the Admin token.
    ok_member = await client.patch(
        "/api/member/profile", json={"bio": "hello"}, headers={"X-CSRF-Token": member_csrf}
    )
    assert ok_member.status_code == 200, ok_member.text

    bad_member = await client.patch(
        "/api/member/profile", json={"bio": "nope"}, headers={"X-CSRF-Token": admin_csrf}
    )
    assert bad_member.status_code == 403
    assert bad_member.json()["error"]["code"] == "CSRF_INVALID"


async def test_missing_csrf_rejected_in_both_realms(client, make_admin, fetch_csrf, monkeypatch):
    await _provision_member(client, make_admin, fetch_csrf, monkeypatch)
    await member_login(client, "coexist@example.com")

    admin_res = await client.post("/api/clients", json={"name": "NoCsrf"})
    assert admin_res.status_code == 403
    assert admin_res.json()["error"]["code"] == "CSRF_MISSING"

    member_res = await client.patch("/api/member/profile", json={"bio": "x"})
    assert member_res.status_code == 403
    assert member_res.json()["error"]["code"] == "CSRF_MISSING"


# ---------------------------------------------------------------------------
# Tokens are realm-scoped even if presented under the other cookie
# ---------------------------------------------------------------------------
async def test_member_token_is_rejected_as_admin_session(client, make_admin, fetch_csrf, monkeypatch):
    settings = get_settings()
    await _provision_member(client, make_admin, fetch_csrf, monkeypatch)

    async with _second_client() as member_client:
        await member_login(member_client, "coexist@example.com")
        member_jwt = member_client.cookies.get(settings.MEMBER_COOKIE_NAME)
        assert member_jwt

    async with _second_client({settings.COOKIE_NAME: member_jwt}) as probe:
        # Member JWT presented as the Admin session cookie must be refused.
        res = await probe.get("/api/auth/me")
        assert res.status_code == 401
    # Sanity check: the same token is valid under its own cookie.
    async with _second_client({settings.MEMBER_COOKIE_NAME: member_jwt}) as probe:
        same = await probe.get("/api/member/me")
        assert same.status_code == 200


async def test_admin_token_is_rejected_as_member_session(client, make_admin, fetch_csrf, monkeypatch):
    settings = get_settings()
    await login_admin(client, make_admin, fetch_csrf)
    # Grab the Admin JWT from the jar.
    admin_jwt = client.cookies.get(settings.COOKIE_NAME)
    assert admin_jwt

    async with _second_client({settings.MEMBER_COOKIE_NAME: admin_jwt}) as probe:
        res = await probe.get("/api/member/me")
        assert res.status_code == 401


# ---------------------------------------------------------------------------
# Cookie scoping / flags
# ---------------------------------------------------------------------------
async def test_session_cookies_are_distinct(client, make_admin, fetch_csrf, monkeypatch):
    settings = get_settings()
    await _provision_member(client, make_admin, fetch_csrf, monkeypatch)
    await member_login(client, "coexist@example.com")

    assert client.cookies.get(settings.COOKIE_NAME)
    assert client.cookies.get(settings.MEMBER_COOKIE_NAME)
    assert client.cookies.get(settings.COOKIE_NAME) != client.cookies.get(
        settings.MEMBER_COOKIE_NAME
    )
    assert client.cookies.get(settings.CSRF_COOKIE_NAME)
    assert client.cookies.get(settings.MEMBER_CSRF_COOKIE_NAME)


async def test_member_cookie_flags(client, make_admin, fetch_csrf, monkeypatch):
    settings = get_settings()
    await _provision_member(client, make_admin, fetch_csrf, monkeypatch)

    csrf_res = await client.get("/api/member/csrf")
    csrf_header = next(
        h
        for h in csrf_res.headers.get_list("set-cookie")
        if h.startswith(f"{settings.MEMBER_CSRF_COOKIE_NAME}=")
    )
    # The CSRF cookie must be readable by JS (NOT HttpOnly).
    assert "httponly" not in csrf_header.lower()

    login_res = await client.post(
        "/api/member/login",
        json={"email": "coexist@example.com", "password": MEMBER_PASSWORD},
        headers={"X-CSRF-Token": csrf_res.json()["csrfToken"]},
    )
    assert login_res.status_code == 200, login_res.text
    session_header = next(
        h
        for h in login_res.headers.get_list("set-cookie")
        if h.startswith(f"{settings.MEMBER_COOKIE_NAME}=")
    )
    assert "httponly" in session_header.lower()
    assert "samesite=" in session_header.lower()


# ---------------------------------------------------------------------------
# Revocation stays realm-local
# ---------------------------------------------------------------------------
async def test_deactivating_member_does_not_affect_admin(client, make_admin, fetch_csrf, monkeypatch):
    await _provision_member(client, make_admin, fetch_csrf, monkeypatch)
    member = (await client.get("/api/members")).json()["items"][0]
    await member_login(client, "coexist@example.com")
    assert (await client.get("/api/member/me")).status_code == 200

    admin_csrf = (await client.get("/api/auth/csrf")).json()["csrfToken"]
    res = await client.post(
        f"/api/members/{member['id']}/deactivate",
        headers={"X-CSRF-Token": admin_csrf},
    )
    assert res.status_code == 200, res.text

    # Only the member session is revoked; the Admin session is untouched.
    assert (await client.get("/api/member/me")).status_code == 401
    assert (await client.get("/api/auth/me")).status_code == 200
