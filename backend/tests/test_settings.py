"""Settings API tests: singleton behavior, admin read/PUT/PATCH, validation,
safe public response, RBAC/CSRF."""

from __future__ import annotations

from app.db.mongo import get_mongo
from app.models.admin import Role

from tests._content_helpers import login_admin


async def _settings_count() -> int:
    return await get_mongo().database["settings"].count_documents({})


async def test_public_get_returns_defaults_without_persisting(client):
    res = await client.get("/api/public/settings")
    assert res.status_code == 200
    body = res.json()
    assert body["general"]["site_name"] == "Thridha Labs"
    assert body["social"]["urls"] == {}
    assert await _settings_count() == 0


async def test_public_response_never_exposes_internal_config(client):
    res = await client.get("/api/public/settings")
    body = res.json()
    assert "analytics" not in body
    assert "id" not in body
    assert "created_at" not in body
    # maintenance_mode is public by design: a plain boolean the frontend
    # gate needs to render the maintenance page.
    assert body["maintenance_mode"] is False
    assert set(body) == {"general", "contact", "social", "footer", "seo", "maintenance_mode"}


async def test_admin_get_requires_auth(client):
    assert (await client.get("/api/settings")).status_code == 401


async def test_put_creates_singleton_and_replaces(client, make_admin, fetch_csrf):
    token = await login_admin(client, make_admin, fetch_csrf)
    res = await client.put(
        "/api/settings",
        json={
            "general": {"site_name": "My Studio"},
            "social": {"urls": {"linkedin": "https://linkedin.com/in/me"}},
            "seo": {"seo_keywords": ["web", "design"]},
        },
        headers={"X-CSRF-Token": token},
    )
    assert res.status_code == 200, res.text
    body = res.json()
    assert body["general"]["site_name"] == "My Studio"
    assert body["social"]["urls"]["linkedin"] == "https://linkedin.com/in/me"
    assert body["seo"]["seo_keywords"] == ["web", "design"]
    assert await _settings_count() == 1

    # PUT is replace: unspecified sections reset to defaults.
    res2 = await client.put(
        "/api/settings",
        json={"general": {"tagline": "Only this"}},
        headers={"X-CSRF-Token": token},
    )
    body2 = res2.json()
    assert body2["general"]["site_name"] == "Thridha Labs"
    assert body2["general"]["tagline"] == "Only this"
    assert body2["social"]["urls"] == {}
    assert await _settings_count() == 1  # still a singleton


async def test_patch_merges_and_keeps_other_fields(client, make_admin, fetch_csrf):
    token = await login_admin(client, make_admin, fetch_csrf)
    await client.put(
        "/api/settings",
        json={"general": {"site_name": "Studio"}, "maintenance_mode": True},
        headers={"X-CSRF-Token": token},
    )
    res = await client.patch(
        "/api/settings",
        json={"general": {"tagline": "New tag"}},
        headers={"X-CSRF-Token": token},
    )
    body = res.json()
    assert body["general"]["site_name"] == "Studio"
    assert body["general"]["tagline"] == "New tag"
    assert body["maintenance_mode"] is True
    assert await _settings_count() == 1


async def test_social_keys_extend_and_clear(client, make_admin, fetch_csrf):
    token = await login_admin(client, make_admin, fetch_csrf)
    await client.patch(
        "/api/settings",
        json={"social": {"urls": {"github": "https://github.com/me"}}},
        headers={"X-CSRF-Token": token},
    )
    res = await client.patch(
        "/api/settings",
        json={"social": {"urls": {"youtube": "https://youtube.com/@me"}}},
        headers={"X-CSRF-Token": token},
    )
    body = res.json()
    assert set(body["social"]["urls"]) == {"github", "youtube"}
    res2 = await client.patch(
        "/api/settings",
        json={"social": {"urls": {"github": ""}}},
        headers={"X-CSRF-Token": token},
    )
    assert "github" not in res2.json()["social"]["urls"]


async def test_validation_failures(client, make_admin, fetch_csrf):
    token = await login_admin(client, make_admin, fetch_csrf)
    cases = [
        {"contact": {"contact_email": "not-an-email"}},
        {"social": {"urls": {"linkedin": "javascript:alert(1)"}}},
        {"social": {"urls": {"bad key!": "https://x.com"}}},
        {"general": {"site_name": "x" * 500}},
        {"seo": {"seo_keywords": ["k" * 1000]}},
    ]
    for payload in cases:
        res = await client.patch(
            "/api/settings", json=payload, headers={"X-CSRF-Token": token}
        )
        assert res.status_code == 422, (res.status_code, payload, res.text)


async def test_rbac_and_csrf(client, make_admin, fetch_csrf):
    await login_admin(client, make_admin, fetch_csrf, role=Role.OWNER)
    editor = await login_admin(
        client, make_admin, fetch_csrf,
        email="editor@example.com", role=Role.EDITOR,
    )
    # editor may write settings
    res = await client.patch(
        "/api/settings", json={"general": {"tagline": "e"}},
        headers={"X-CSRF-Token": editor},
    )
    assert res.status_code == 200, res.text
    # CSRF required
    res = await client.patch("/api/settings", json={"general": {"site_name": "x"}})
    assert res.status_code == 403 and res.json()["error"]["code"] == "CSRF_MISSING"
    bad = await client.patch(
        "/api/settings", json={"general": {"site_name": "x"}},
        headers={"X-CSRF-Token": "wrong-token"},
    )
    assert bad.status_code == 403 and bad.json()["error"]["code"] == "CSRF_INVALID"