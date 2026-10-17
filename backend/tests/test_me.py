"""GET /api/auth/me — session validation, revocation, expiry, disabled state."""

from __future__ import annotations

from datetime import timedelta

from app.core.config import get_settings
from app.core.security import create_access_token
from app.db.mongo import get_mongo
from app.modules.admins import repository


def _me_with_cookie(client, token_value: str):
    settings = get_settings()
    return client.get(
        "/api/auth/me",
        headers={"Cookie": f"{settings.COOKIE_NAME}={token_value}"},
    )


async def test_me_unauthenticated_is_401(client):
    res = await client.get("/api/auth/me")
    assert res.status_code == 401
    assert res.json()["error"]["code"] == "NOT_AUTHENTICATED"


async def test_me_success(make_admin, client, login):
    admin = await make_admin("me@example.com")
    assert (
        await login("me@example.com", "CorrectHorse!Battery9")
    ).status_code == 200

    res = await client.get("/api/auth/me")  # GET needs no CSRF header
    assert res.status_code == 200
    body = res.json()
    assert set(body) == {"id", "email", "role", "is_active"}
    assert body["id"] == admin.id
    assert body["email"] == "me@example.com"
    assert body["role"] == "owner"
    assert body["is_active"] is True
    assert "password" not in res.text


async def test_me_with_garbage_cookie_is_invalid(make_admin, client, login):
    settings = get_settings()
    await make_admin("garbage@example.com")
    assert (
        await login("garbage@example.com", "CorrectHorse!Battery9")
    ).status_code == 200

    res = await client.get(
        "/api/auth/me", headers={"Cookie": f"{settings.COOKIE_NAME}=not.a.jwt"}
    )
    assert res.status_code == 401
    assert res.json()["error"]["code"] == "TOKEN_INVALID"


async def test_me_with_expired_token(make_admin, client):
    admin = await make_admin("expired@example.com")
    token = create_access_token(
        admin_id=admin.id,
        role=admin.role.value,
        token_version=admin.token_version,
        expires_delta=timedelta(minutes=-5),
    )
    res = await _me_with_cookie(client, token)
    assert res.status_code == 401
    assert res.json()["error"]["code"] == "TOKEN_EXPIRED"


async def test_me_after_token_version_bump_is_revoked(make_admin, client, login):
    admin = await make_admin("revoked@example.com")
    assert (
        await login("revoked@example.com", "CorrectHorse!Battery9")
    ).status_code == 200

    await repository.bump_token_version(admin.id)

    res = await client.get("/api/auth/me")
    assert res.status_code == 401
    assert res.json()["error"]["code"] == "SESSION_REVOKED"


async def test_me_after_account_deleted_is_revoked(make_admin, client, login):
    await make_admin("deleted@example.com")
    assert (
        await login("deleted@example.com", "CorrectHorse!Battery9")
    ).status_code == 200

    await get_mongo().database["admins"].delete_many({})

    res = await client.get("/api/auth/me")
    assert res.status_code == 401
    assert res.json()["error"]["code"] == "SESSION_REVOKED"


async def test_me_for_disabled_account_is_403(make_admin, client, login):
    await make_admin("off@example.com")
    assert (
        await login("off@example.com", "CorrectHorse!Battery9")
    ).status_code == 200

    await get_mongo().database["admins"].update_many(
        {}, {"$set": {"is_active": False}}
    )

    res = await client.get("/api/auth/me")
    assert res.status_code == 403
    assert res.json()["error"]["code"] == "ACCOUNT_DISABLED"


async def test_me_requires_no_csrf(make_admin, client, login):
    await make_admin("nocsrf-me@example.com")
    assert (
        await login("nocsrf-me@example.com", "CorrectHorse!Battery9")
    ).status_code == 200

    # Deliberately no X-CSRF-Token header — GETs are exempt.
    res = await client.get("/api/auth/me")
    assert res.status_code == 200
