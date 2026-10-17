"""Sitemap / robots contract tests.

Sitemap must:
- be served at `/sitemap.xml` with an XML media type
- carry absolute URLs built from the configured FRONTEND_URL
- include every static public route and every published project slug
- never include admin/draft/archived/test content
"""

# ---------------------------------------------------------------------------
from __future__ import annotations

import os

import pytest

from app.core.config import get_settings

_PUBLIC_URL = "https://thridhalabs.example"


@pytest.fixture
def public_frontend_url(monkeypatch):
    monkeypatch.setenv("FRONTEND_URL", _PUBLIC_URL)
    get_settings.cache_clear()
    yield
    monkeypatch.undo()
    get_settings.cache_clear()


async def test_sitemap_includes_public_and_published(client, make_admin, login, fetch_csrf, public_frontend_url):
    await make_admin("owner@example.com")
    await login("owner@example.com", "CorrectHorse!Battery9")
    csrf = await fetch_csrf()

    for name, status in (("Published Lab", "published"), ("Draft Lab", "draft")):
        res = await client.post(
            "/api/projects",
            json={"name": name, "project_type": "experiment", "status": status},
            headers={"X-CSRF-Token": csrf},
        )
        assert res.status_code in (200, 201), res.text

    res = await client.get("/sitemap.xml")
    assert res.status_code == 200
    assert res.headers["content-type"].startswith("application/xml")
    text = res.text

    base = get_settings().FRONTEND_URL
    assert base and base == _PUBLIC_URL
    for path in ("/", "/projects", "/clients", "/testimonials", "/about", "/contact"):
        assert f"<loc>{base.rstrip('/')}{path}</loc>" in text

    assert "/projects/published-lab" in text
    assert "/projects/draft-lab" not in text
    assert "/admin" not in text
    assert "localhost" not in text


async def test_robots_txt_allows_public_and_bans_admin(client, public_frontend_url):
    res = await client.get("/robots.txt")
    assert res.status_code == 200
    assert res.headers["content-type"].startswith("text/plain")
    text = res.text
    assert "Disallow: /admin" in text
    assert "Sitemap: " in text
    assert _PUBLIC_URL in text
    assert "localhost" not in text


async def test_seo_documents_require_configured_public_url(client, monkeypatch):
    monkeypatch.delenv("FRONTEND_URL", raising=False)
    get_settings.cache_clear()
    try:
        res = await client.get("/sitemap.xml")
        assert res.status_code == 503
        res = await client.get("/robots.txt")
        assert res.status_code == 503
    finally:
        monkeypatch.undo()
        get_settings.cache_clear()