"""CSRF double-submit: bootstrap endpoint, exemptions, enforcement."""

from __future__ import annotations

from app.core.config import get_settings


async def test_csrf_bootstrap_returns_token_and_readable_cookie(client):
    settings = get_settings()
    res = await client.get("/api/auth/csrf")
    assert res.status_code == 200

    token = res.json()["csrfToken"]
    assert token and len(token) > 20

    cookie_header = next(
        h
        for h in res.headers.get_list("set-cookie")
        if h.startswith(settings.CSRF_COOKIE_NAME + "=")
    )
    assert "HttpOnly" not in cookie_header, "double-submit requires JS-readable cookie"
    assert "Secure" in cookie_header

    # Body token and cookie value must match (double-submit pair).
    assert token in cookie_header


async def test_get_endpoints_do_not_require_csrf(client):
    res = await client.get("/api/auth/me")
    # 401 (unauthenticated), never 403 CSRF — GETs are exempt.
    assert res.status_code == 401
    assert res.json()["error"]["code"] == "NOT_AUTHENTICATED"


async def test_post_without_any_csrf_is_rejected(client):
    res = await client.post(
        "/api/auth/login",
        json={"email": "x@example.com", "password": "whatever"},
    )
    assert res.status_code == 403
    assert res.json()["error"]["code"] == "CSRF_MISSING"


async def test_post_with_header_but_no_cookie_is_rejected(client):
    res = await client.post(
        "/api/auth/login",
        json={"email": "x@example.com", "password": "whatever"},
        headers={"X-CSRF-Token": "header-only-token"},
    )
    assert res.status_code == 403
    assert res.json()["error"]["code"] == "CSRF_MISSING"


async def test_post_with_mismatched_pair_is_rejected(client):
    await client.get("/api/auth/csrf")  # sets a real cookie
    res = await client.post(
        "/api/auth/login",
        json={"email": "x@example.com", "password": "whatever"},
        headers={"X-CSRF-Token": "a-totally-different-token"},
    )
    assert res.status_code == 403
    assert res.json()["error"]["code"] == "CSRF_INVALID"


async def test_post_with_matching_pair_passes_csrf_gate(make_admin, client, fetch_csrf):
    await make_admin("pair@example.com")
    token = await fetch_csrf()  # bootstrap: cookie is set, body token returned
    res = await client.post(
        "/api/auth/login",
        json={"email": "pair@example.com", "password": "CorrectHorse!Battery9"},
        headers={"X-CSRF-Token": token},
    )
    assert res.status_code == 200
