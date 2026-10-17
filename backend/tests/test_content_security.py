"""Cross-cutting security tests for Phase 4 content APIs:
no internal leakage, consistent 404s for hidden public resources,
unsafe sort/filter injection is rejected, and 401/403 semantics hold."""

from __future__ import annotations

from tests._content_helpers import (
    create_client,
    create_project,
    create_testimonial,
    login_admin,
)


async def test_public_responses_have_no_internal_identifiers(client, make_admin, fetch_csrf):
    token = await login_admin(client, make_admin, fetch_csrf)
    c = await create_client(client, token, name="Omega Corp")
    p1 = await create_project(client, token, name="Visible", project_type="product",
                              status="published", client_id=c["id"])
    p2 = await create_project(client, token, name="Drafty", project_type="product",
                              status="draft", client_id=c["id"])
    await create_project(client, token, name="Born Ledger", project_type="experiment",
                         status="published", client_id=c["id"])

    res = await client.get("/api/public/projects")
    assert res.status_code == 200
    for item in res.json()["items"]:
        assert "id" not in item
        assert "client_id" not in item
        assert "created_at" not in item
        assert "updated_at" not in item
        # client ref is a public slug, not an internal id
        assert "slug" in item["client"] and "id" not in item["client"]

    res = await client.get("/api/public/clients")
    for item in res.json()["items"]:
        assert "id" not in item
        assert "created_at" not in item

    assert p1 and p2  # created during setup


async def test_public_branding_settings_have_no_internal_keys(client, make_admin, fetch_csrf):
    token = await login_admin(client, make_admin, fetch_csrf)
    await client.put("/api/settings", json={"general": {"site_name": "X"}},
                     headers={"X-CSRF-Token": token})
    settings = (await client.get("/api/public/settings")).json()
    assert "analytics" not in settings
    # maintenance_mode is public by design: it is plain system state that the
    # frontend needs to route public traffic to the maintenance page, and it
    # reveals no credentials or secrets.
    assert settings["maintenance_mode"] is False
    branding = (await client.get("/api/public/branding")).json()
    assert set(branding["media"]) == {
        "logo", "logo_dark", "logo_light", "favicon", "og_image",
    }


async def test_unsafe_filter_and_sort_injection_rejected(client, make_admin, fetch_csrf):
    await login_admin(client, make_admin, fetch_csrf)  # auth so failures are real
    for path in (
        "/api/clients?sort=$where",
        "/api/projects?sort=display_order;db.projects.drop()",
        "/api/testimonials?sort=__proto__",
        "/api/clients?page=-1",
        "/api/clients?page_size=1000",
    ):
        res = await client.get(path)
        assert res.status_code in (400, 422), (path, res.status_code, res.text)


async def test_filter_operator_params_ignored(client, make_admin, fetch_csrf):
    """Unknown keys such as Mongo operator syntax are silently ignored — the
    query dict is only ever built from explicitly declared parameters, so no
    `$` operator can reach the database."""
    await login_admin(client, make_admin, fetch_csrf)
    for path in (
        "/api/clients?category[$ne]=y",
        "/api/projects?status[$regex]=published",
        "/api/clients?industry[$gt]=x&name[$exists]=1",
    ):
        res = await client.get(path)
        assert res.status_code == 200, (path, res.status_code, res.text)
        assert res.json()["items"] == []


async def test_admin_http_verb_and_auth_matrix(client, fetch_csrf):
    token = await fetch_csrf()  # CSRF passes; auth must still fail with 401
    for path in (
        "/api/settings",
        "/api/branding",
        "/api/clients",
        "/api/projects",
        "/api/testimonials",
    ):
        res = await client.get(path)
        assert res.status_code == 401, (path, res.status_code)
    for path in ("/api/settings", "/api/branding"):
        res = await client.put(path, json={}, headers={"X-CSRF-Token": token})
        assert res.status_code == 401, ("PUT", path, res.status_code)
    for path in ("/api/clients", "/api/projects", "/api/testimonials"):
        res = await client.post(path, json={}, headers={"X-CSRF-Token": token})
        assert res.status_code == 401, ("POST", path, res.status_code)

    for path in (
        "/api/public/settings",
        "/api/public/branding",
        "/api/public/clients",
        "/api/public/projects",
        "/api/public/testimonials",
    ):
        res = await client.get(path)
        assert res.status_code == 200, (path, res.status_code)


async def test_unauth_write_without_csrf_yields_403(client):
    for path in ("/api/clients", "/api/projects", "/api/testimonials"):
        res = await client.post(path, json={})
        assert res.status_code == 403, (path, res.status_code)


async def test_unpublish_removes_from_public_instantly(client, make_admin, fetch_csrf):
    token = await login_admin(client, make_admin, fetch_csrf)
    proj = await create_project(client, token, name="Live", project_type="product", status="published")
    assert (await client.get("/api/public/projects/live")).status_code == 200
    res = await client.patch(
        f"/api/projects/{proj['id']}", json={"status": "archived"},
        headers={"X-CSRF-Token": token},
    )
    assert res.status_code == 200
    assert (await client.get("/api/public/projects/live")).status_code == 404

    testi = await create_testimonial(client, token, person_name="Gone", published=True)
    assert (await client.get(f"/api/public/testimonials/{testi['id']}")).status_code == 200
    res = await client.patch(
        f"/api/testimonials/{testi['id']}", json={"published": False},
        headers={"X-CSRF-Token": token},
    )
    assert res.status_code == 200
    assert (await client.get(f"/api/public/testimonials/{testi['id']}")).status_code == 404


async def test_slug_collision_across_entity_types_is_fine(client, make_admin, fetch_csrf):
    token = await login_admin(client, make_admin, fetch_csrf)
    await create_client(client, token, name="Launch")
    await create_project(client, token, name="Launch", project_type="product", status="published")
    # slugs live in separate collections, so no conflict here
    assert (await client.get("/api/public/clients/launch")).status_code == 200
    assert (await client.get("/api/public/projects/launch")).status_code == 200