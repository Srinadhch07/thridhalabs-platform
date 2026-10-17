"""Branding API tests: singleton, admin PUT, media reference validation,
public response, RBAC/CSRF."""

from __future__ import annotations

from app.db.mongo import get_mongo
from app.models.admin import Role

from tests._content_helpers import login_admin, upload_media


async def _branding_count() -> int:
    return await get_mongo().database["branding"].count_documents({})


async def test_public_get_returns_defaults_without_persisting(client):
    res = await client.get("/api/public/branding")
    assert res.status_code == 200
    body = res.json()
    assert body["colors"]["primary"] == "#4f46e5"
    assert body["mode"] == "light"
    assert body["media"] == {
        "logo": None, "logo_dark": None, "logo_light": None,
        "favicon": None, "og_image": None,
    }
    assert await _branding_count() == 0


async def test_admin_put_creates_singleton(client, make_admin, fetch_csrf):
    token = await login_admin(client, make_admin, fetch_csrf)
    res = await client.put(
        "/api/branding",
        json={"colors": {"primary": "#0f766e"}, "mode": "dark"},
        headers={"X-CSRF-Token": token},
    )
    assert res.status_code == 200, res.text
    body = res.json()
    assert body["colors"]["primary"] == "#0f766e"
    assert body["mode"] == "dark"
    assert body["colors"]["secondary"] == "#0ea5e9"  # unspecified kept at default
    assert await _branding_count() == 1


async def test_put_replaces_unspecified(client, make_admin, fetch_csrf):
    token = await login_admin(client, make_admin, fetch_csrf)
    await client.put(
        "/api/branding", json={"colors": {"primary": "#ff0000"}, "mode": "dark"},
        headers={"X-CSRF-Token": token},
    )
    res = await client.put(
        "/api/branding", json={"mode": "light"},
        headers={"X-CSRF-Token": token},
    )
    body = res.json()
    assert body["mode"] == "light"
    assert body["colors"]["primary"] == "#4f46e5"  # replaced with defaults
    assert await _branding_count() == 1


async def test_theme_preset_accepted_and_persisted(client, make_admin, fetch_csrf):
    token = await login_admin(client, make_admin, fetch_csrf)
    res = await client.put(
        "/api/branding",
        json={"theme_preset": "midnight_slate", "mode": "dark", "colors": {"primary": "#60a5fa"}},
        headers={"X-CSRF-Token": token},
    )
    assert res.status_code == 200, res.text
    body = res.json()
    assert body["theme_preset"] == "midnight_slate"
    assert body["mode"] == "dark"

    pub = await client.get("/api/public/branding")
    pub_body = pub.json()
    assert "theme_preset" not in pub_body  # public contract unchanged
    assert pub_body["colors"]["primary"] == "#60a5fa"


async def test_unknown_theme_preset_rejected(client, make_admin, fetch_csrf):
    token = await login_admin(client, make_admin, fetch_csrf)
    res = await client.put(
        "/api/branding", json={"theme_preset": "chartreuse"},
        headers={"X-CSRF-Token": token},
    )
    assert res.status_code == 422

    res = await client.put("/api/branding", json={"mode": "light"},
                           headers={"X-CSRF-Token": token})
    assert res.status_code == 200
    assert res.json()["theme_preset"] is None


async def test_put_without_theme_preset_resets_null(client, make_admin, fetch_csrf):
    token = await login_admin(client, make_admin, fetch_csrf)
    await client.put(
        "/api/branding", json={"theme_preset": "pearl_emerald", "colors": {"primary": "#059669"}},
        headers={"X-CSRF-Token": token},
    )
    res = await client.put(
        "/api/branding", json={"theme_preset": None, "colors": {"primary": "#059669"}},
        headers={"X-CSRF-Token": token},
    )
    assert res.status_code == 200
    assert res.json()["theme_preset"] is None
    assert await _branding_count() == 1


async def test_invalid_hex_rejected(client, make_admin, fetch_csrf):
    token = await login_admin(client, make_admin, fetch_csrf)
    res = await client.put(
        "/api/branding", json={"colors": {"primary": "red"}},
        headers={"X-CSRF-Token": token},
    )
    assert res.status_code == 422


async def test_valid_media_references_accepted(client, make_admin, fetch_csrf):
    token = await login_admin(client, make_admin, fetch_csrf)
    media = await upload_media(client, token)
    res = await client.put(
        "/api/branding",
        json={"media": {"logo": media["id"], "favicon": media["id"]}},
        headers={"X-CSRF-Token": token},
    )
    assert res.status_code == 200, res.text
    assert res.json()["media"]["logo"] == media["id"]


async def test_missing_media_reference_rejected(client, make_admin, fetch_csrf):
    token = await login_admin(client, make_admin, fetch_csrf)
    res = await client.put(
        "/api/branding",
        json={"media": {"logo": "60f000000000000000000000"}},
        headers={"X-CSRF-Token": token},
    )
    assert res.status_code == 400
    assert res.json()["error"]["code"] == "INVALID_MEDIA_REFERENCE"


async def test_public_response_is_presentation_only(client, make_admin, fetch_csrf):
    token = await login_admin(client, make_admin, fetch_csrf)
    media = await upload_media(client, token)
    await client.put(
        "/api/branding",
        json={"colors": {"accent": "#123abc"}, "media": {"logo": media["id"]}},
        headers={"X-CSRF-Token": token},
    )
    res = await client.get("/api/public/branding")
    body = res.json()
    assert body["colors"]["accent"] == "#123abc"
    assert body["media"]["logo"] == media["id"]
    assert "id" not in body and "created_at" not in body


async def test_auth_and_csrf(client, make_admin, fetch_csrf):
    assert (await client.get("/api/branding")).status_code == 401
    token = await login_admin(client, make_admin, fetch_csrf, role=Role.EDITOR)
    res = await client.put("/api/branding", json={"mode": "dark"})
    assert res.status_code == 403 and res.json()["error"]["code"] == "CSRF_MISSING"
    ok = await client.put(
        "/api/branding", json={"mode": "dark"}, headers={"X-CSRF-Token": token}
    )
    assert ok.status_code == 200