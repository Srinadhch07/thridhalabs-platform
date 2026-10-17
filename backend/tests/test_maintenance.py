"""Maintenance-mode enforcement tests.

When `maintenance_mode` is on, public *content* endpoints answer 503 with a
stable code instead of serving content, while admin APIs, auth, health,
sitemap/robots and the public settings/branding endpoints keep working.
"""

from __future__ import annotations

import pytest

from app.core.config import get_settings
from tests._content_helpers import login_admin


@pytest.fixture
def public_frontend_url(monkeypatch):
    monkeypatch.setenv("FRONTEND_URL", "https://thridhalabs.example")
    get_settings.cache_clear()
    yield
    monkeypatch.undo()
    get_settings.cache_clear()


async def _set_maintenance(client, token: str, enabled: bool):
    res = await client.put(
        "/api/settings",
        json={"maintenance_mode": enabled},
        headers={"X-CSRF-Token": token},
    )
    assert res.status_code == 200, res.text


async def test_public_content_served_when_maintenance_off(client):
    for path in (
        "/api/public/projects",
        "/api/public/clients",
        "/api/public/testimonials",
    ):
        res = await client.get(path)
        assert res.status_code == 200, (path, res.text)


async def test_maintenance_blocks_public_content_not_admin(
    client, make_admin, fetch_csrf, public_frontend_url
):
    token = await login_admin(client, make_admin, fetch_csrf)
    await _set_maintenance(client, token, True)

    try:
        for path in (
            "/api/public/projects",
            "/api/public/clients",
            "/api/public/testimonials",
        ):
            res = await client.get(path)
            assert res.status_code == 503, (path, res.text)
            assert res.json()["error"]["code"] == "MAINTENANCE_MODE"

        # Public submission follows the same policy: blocked, not stored.
        res = await client.post(
            "/api/public/testimonials",
            json={"person_name": "Nobody", "testimonial_text": "Offline words."},
        )
        assert res.status_code == 503
        assert res.json()["error"]["code"] == "MAINTENANCE_MODE"

        # Public media delivery is content too.
        res = await client.get("/api/public/media/000000000000000000000000")
        assert res.status_code == 503

        # Everything the owner needs keeps working.
        assert (await client.get("/api/public/settings")).status_code == 200
        assert (await client.get("/api/public/branding")).status_code == 200
        assert (await client.get("/api/health")).status_code == 200
        assert (await client.get("/api/health/ready")).status_code == 200
        assert (await client.get("/api/auth/me")).status_code == 200
        assert (await client.get("/api/testimonials")).status_code == 200
        assert (await client.get("/api/settings")).status_code == 200
        assert (await client.get("/sitemap.xml")).status_code == 200
        assert (await client.get("/robots.txt")).status_code == 200
    finally:
        await _set_maintenance(client, token, False)

    res = await client.get("/api/public/projects")
    assert res.status_code == 200
