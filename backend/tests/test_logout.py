"""POST /api/auth/logout — cookie clearing and session revocation."""

from __future__ import annotations

from app.core.config import get_settings


async def test_logout_clears_cookies(make_admin, client, login, logout):
    settings = get_settings()
    await make_admin("bye@example.com")
    assert (
        await login("bye@example.com", "CorrectHorse!Battery9")
    ).status_code == 200

    res = await logout()
    assert res.status_code == 200
    assert res.json() == {"status": "ok"}

    cleared = res.headers.get_list("set-cookie")
    auth_clear = next(h for h in cleared if h.startswith(settings.COOKIE_NAME + "="))
    csrf_clear = next(h for h in cleared if h.startswith(settings.CSRF_COOKIE_NAME + "="))
    assert f'{settings.COOKIE_NAME}=""' in auth_clear
    assert f'{settings.CSRF_COOKIE_NAME}=""' in csrf_clear
    assert "Max-Age=0" in auth_clear

    # Session cookie is no longer usable.
    assert (await client.get("/api/auth/me")).status_code == 401


async def test_old_token_is_revoked_after_logout(make_admin, client, login, logout):
    settings = get_settings()
    await make_admin("revoked2@example.com")
    assert (
        await login("revoked2@example.com", "CorrectHorse!Battery9")
    ).status_code == 200

    stolen_token = client.cookies.get(settings.COOKIE_NAME)
    assert stolen_token

    assert (await logout()).status_code == 200

    # The jar no longer has the cookie, but replay it manually as a stolen
    # token would: token_version was bumped, so it must be rejected.
    res = await client.get(
        "/api/auth/me",
        headers={"Cookie": f"{settings.COOKIE_NAME}={stolen_token}"},
    )
    assert res.status_code == 401
    assert res.json()["error"]["code"] == "SESSION_REVOKED"


async def test_logout_requires_authentication(client, fetch_csrf):
    token = await fetch_csrf()
    res = await client.post("/api/auth/logout", headers={"X-CSRF-Token": token})
    assert res.status_code == 401
    assert res.json()["error"]["code"] == "NOT_AUTHENTICATED"


async def test_logout_requires_csrf(make_admin, client, login):
    await make_admin("csrf-logout@example.com")
    assert (
        await login("csrf-logout@example.com", "CorrectHorse!Battery9")
    ).status_code == 200

    res = await client.post("/api/auth/logout")  # no X-CSRF-Token header
    assert res.status_code == 403
    assert res.json()["error"]["code"] == "CSRF_MISSING"

    # Session must still be alive (no side effects on CSRF failure).
    assert (await client.get("/api/auth/me")).status_code == 200


async def test_logout_twice_second_fails(make_admin, client, login, logout):
    await make_admin("twice@example.com")
    assert (
        await login("twice@example.com", "CorrectHorse!Battery9")
    ).status_code == 200

    assert (await logout()).status_code == 200
    second = await logout()
    assert second.status_code == 401
