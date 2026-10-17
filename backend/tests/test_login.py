"""POST /api/auth/login — credentials, cookie policy, CSRF, responses."""

from __future__ import annotations

from app.core.config import get_settings
from app.db.mongo import get_mongo

def _set_cookies(res) -> list[str]:
    return res.headers.get_list("set-cookie")


def _find_cookie(res, name: str) -> str:
    cookies = _set_cookies(res)
    for header in cookies:
        if header.startswith(name + "="):
            return header
    raise AssertionError(f"no Set-Cookie for {name!r} in {cookies}")


async def test_successful_login_sets_cookies_and_returns_no_token(
    make_admin, client, csrf_token
):
    settings = get_settings()
    await make_admin("owner@example.com")

    res = await client.post(
        "/api/auth/login",
        json={"email": "owner@example.com", "password": "CorrectHorse!Battery9"},
        headers={"X-CSRF-Token": csrf_token},
    )

    assert res.status_code == 200
    body = res.json()
    assert body == {"status": "ok"}
    # The JWT must never appear in the response body.
    assert "token" not in body
    assert "jwt" not in body

    auth_header = _find_cookie(res, settings.COOKIE_NAME)
    assert "HttpOnly" in auth_header
    assert "Secure" in auth_header
    assert "SameSite=none" in auth_header
    assert "Path=/" in auth_header

    csrf_header = _find_cookie(res, settings.CSRF_COOKIE_NAME)
    assert "HttpOnly" not in csrf_header, "CSRF cookie must be readable by JS"


async def test_login_with_wrong_password_is_generic_401(make_admin, client, csrf_token):
    await make_admin("wrongpw@example.com")
    res = await client.post(
        "/api/auth/login",
        json={"email": "wrongpw@example.com", "password": "NotThePassword1!"},
        headers={"X-CSRF-Token": csrf_token},
    )
    assert res.status_code == 401
    error = res.json()["error"]
    assert error["code"] == "INVALID_CREDENTIALS"
    assert error["message"] == "Invalid email or password"


async def test_unknown_email_is_indistinguishable_from_wrong_password(
    make_admin, client, csrf_token
):
    await make_admin("known@example.com")

    wrong_pw = await client.post(
        "/api/auth/login",
        json={"email": "known@example.com", "password": "NotThePassword1!"},
        headers={"X-CSRF-Token": csrf_token},
    )
    unknown = await client.post(
        "/api/auth/login",
        json={"email": "nobody@example.com", "password": "NotThePassword1!"},
        headers={"X-CSRF-Token": csrf_token},
    )

    assert wrong_pw.status_code == unknown.status_code == 401
    assert wrong_pw.json() == unknown.json(), "responses must be identical"


async def test_inactive_account_cannot_log_in(make_admin, client, csrf_token):
    await make_admin("disabled@example.com", is_active=False)
    res = await client.post(
        "/api/auth/login",
        json={"email": "disabled@example.com", "password": "CorrectHorse!Battery9"},
        headers={"X-CSRF-Token": csrf_token},
    )
    assert res.status_code == 403
    assert res.json()["error"]["code"] == "ACCOUNT_DISABLED"


async def test_login_normalizes_email(make_admin, client, csrf_token):
    await make_admin("mixed@example.com")
    res = await client.post(
        "/api/auth/login",
        json={"email": "  MIXED@Example.com  ", "password": "CorrectHorse!Battery9"},
        headers={"X-CSRF-Token": csrf_token},
    )
    assert res.status_code == 200


async def test_login_requires_csrf_header(make_admin, client):
    await make_admin("nocsrf@example.com")
    res = await client.post(
        "/api/auth/login",
        json={"email": "nocsrf@example.com", "password": "CorrectHorse!Battery9"},
    )
    assert res.status_code == 403
    assert res.json()["error"]["code"] == "CSRF_MISSING"


async def test_login_rejects_mismatched_csrf(make_admin, client, fetch_csrf):
    await fetch_csrf()  # sets a real cookie
    await make_admin("badcsrf@example.com")
    res = await client.post(
        "/api/auth/login",
        json={"email": "badcsrf@example.com", "password": "CorrectHorse!Battery9"},
        headers={"X-CSRF-Token": "not-the-cookie-value"},
    )
    assert res.status_code == 403
    assert res.json()["error"]["code"] == "CSRF_INVALID"


async def test_successful_login_records_last_login(make_admin, login):
    admin = await make_admin("stamped@example.com")
    res = await login("stamped@example.com", "CorrectHorse!Battery9")
    assert res.status_code == 200

    doc = await get_mongo().database["admins"].find_one({"email": "stamped@example.com"})
    assert doc["last_login_at"] is not None
    assert doc["email"] == admin.email


async def test_validation_error_does_not_echo_password(client, csrf_token):
    res = await client.post(
        "/api/auth/login",
        json={"email": "not-an-email", "password": "Sup3rSecret!Passw0rd"},
        headers={"X-CSRF-Token": csrf_token},
    )
    assert res.status_code == 422
    body = res.json()
    assert body["error"]["code"] == "VALIDATION_ERROR"
    assert "Sup3rSecret!Passw0rd" not in res.text


async def test_validation_error_missing_fields(client, csrf_token):
    res = await client.post(
        "/api/auth/login", json={}, headers={"X-CSRF-Token": csrf_token}
    )
    assert res.status_code == 422
    assert res.json()["error"]["code"] == "VALIDATION_ERROR"


async def test_login_with_empty_password_is_rejected_by_validation(
    make_admin, client, csrf_token
):
    await make_admin("emptypw@example.com")
    res = await client.post(
        "/api/auth/login",
        json={"email": "emptypw@example.com", "password": ""},
        headers={"X-CSRF-Token": csrf_token},
    )
    assert res.status_code == 422
