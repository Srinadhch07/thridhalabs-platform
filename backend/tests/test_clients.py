"""Clients API tests: CRUD, slugs, pagination/filters/sorting, RBAC/CSRF,
media references, delete-blocking, public visibility."""

from __future__ import annotations

from app.models.admin import Role

from tests._content_helpers import (
    create_client,
    create_project,
    create_testimonial,
    login_admin,
    upload_media,
)


# --------------------------------------------------------------------------
# create / slugs
# --------------------------------------------------------------------------
async def test_create_generates_slug(client, make_admin, fetch_csrf):
    token = await login_admin(client, make_admin, fetch_csrf)
    res = await client.post(
        "/api/clients",
        json={"name": "Acme Motors"},
        headers={"X-CSRF-Token": token},
    )
    assert res.status_code == 201, res.text
    body = res.json()
    assert body["slug"] == "acme-motors"
    assert body["display_order"] == 0 and body["featured"] is False


async def test_create_with_explicit_slug(client, make_admin, fetch_csrf):
    token = await login_admin(client, make_admin, fetch_csrf)
    res = await client.post(
        "/api/clients",
        json={"name": "UrbanZoomIN", "slug": "urban-zoomin"},
        headers={"X-CSRF-Token": token},
    )
    assert res.status_code == 201, res.text
    assert res.json()["slug"] == "urban-zoomin"


async def test_explicit_slug_conflict_rejected(client, make_admin, fetch_csrf):
    token = await login_admin(client, make_admin, fetch_csrf)
    await create_client(client, token, name="First", slug="shared")
    res = await client.post(
        "/api/clients",
        json={"name": "Second", "slug": "shared"},
        headers={"X-CSRF-Token": token},
    )
    assert res.status_code == 409
    assert res.json()["error"]["code"] == "SLUG_TAKEN"


async def test_generated_slug_collision_gets_suffix(client, make_admin, fetch_csrf):
    token = await login_admin(client, make_admin, fetch_csrf)
    await create_client(client, token, name="Acme Motors")
    created = await create_client(client, token, name="Acme Motors")
    assert created["slug"] == "acme-motors-2"


async def test_invalid_slug_rejected(client, make_admin, fetch_csrf):
    token = await login_admin(client, make_admin, fetch_csrf)
    res = await client.post(
        "/api/clients",
        json={"name": "X", "slug": "../traversal"},
        headers={"X-CSRF-Token": token},
    )
    assert res.status_code == 422
    assert "SLUG" in res.json()["error"]["code"] or res.json()["error"]["code"] == "VALIDATION_ERROR"


async def test_name_with_only_symbols_needs_slug(client, make_admin, fetch_csrf):
    token = await login_admin(client, make_admin, fetch_csrf)
    res = await client.post(
        "/api/clients",
        json={"name": "!!!", "slug": "lit"},
        headers={"X-CSRF-Token": token},
    )
    assert res.status_code == 201
    assert res.json()["slug"] == "lit"


# --------------------------------------------------------------------------
# read / list
# --------------------------------------------------------------------------
async def test_get_and_list(client, make_admin, fetch_csrf):
    token = await login_admin(client, make_admin, fetch_csrf)
    created = await create_client(client, token, name="Quantum", featured=True, display_order=2)
    got = await client.get(f"/api/clients/{created['id']}")
    assert got.status_code == 200
    assert got.json()["name"] == "Quantum"

    listed = await client.get("/api/clients")
    assert listed.status_code == 200
    payload = listed.json()
    assert payload["total"] == 1
    assert payload["pages"] == 1
    assert payload["items"][0]["id"] == created["id"]


async def test_filters_and_pagination(client, make_admin, fetch_csrf):
    token = await login_admin(client, make_admin, fetch_csrf)
    await create_client(client, token, name="A", category="tech", industry="saas", featured=True)
    await create_client(client, token, name="B", category="retail", industry="food")
    await create_client(client, token, name="C", category="tech")

    r = await client.get("/api/clients?category=tech")
    assert r.json()["total"] == 2
    r = await client.get("/api/clients?industry=saas")
    assert r.json()["total"] == 1
    r = await client.get("/api/clients?featured=true")
    assert r.json()["total"] == 1 and r.json()["items"][0]["name"] == "A"
    r = await client.get("/api/clients?page=1&page_size=1")
    assert len(r.json()["items"]) == 1 and r.json()["total"] == 3


async def test_sorting(client, make_admin, fetch_csrf):
    token = await login_admin(client, make_admin, fetch_csrf)
    await create_client(client, token, name="Zed", display_order=1)
    await create_client(client, token, name="Alpine", display_order=0)
    r = await client.get("/api/clients?sort=display_order&order=asc")
    names = [item["name"] for item in r.json()["items"]]
    assert names == ["Alpine", "Zed"]
    r = await client.get("/api/clients?sort=name&order=desc")
    names = [item["name"] for item in r.json()["items"]]
    assert names == ["Zed", "Alpine"]
    bad = await client.get("/api/clients?sort=eve;drop()")
    assert bad.status_code == 422


async def test_missing_client_404(client, make_admin, fetch_csrf):
    token = await login_admin(client, make_admin, fetch_csrf)
    res = await client.get("/api/clients/000000000000000000000000")
    assert res.status_code == 404
    assert res.json()["error"]["code"] == "CLIENT_NOT_FOUND"
    assert token  # silence unused


# --------------------------------------------------------------------------
# update
# --------------------------------------------------------------------------
async def test_patch_keeps_slug_on_name_change(client, make_admin, fetch_csrf):
    token = await login_admin(client, make_admin, fetch_csrf)
    created = await create_client(client, token, name="Old Name")
    res = await client.patch(
        f"/api/clients/{created['id']}",
        json={"name": "New Name", "industry": "ai"},
        headers={"X-CSRF-Token": token},
    )
    assert res.status_code == 200
    body = res.json()
    assert body["name"] == "New Name"
    assert body["slug"] == "old-name"  # slug not silently regenerated
    assert body["industry"] == "ai"


async def test_patch_explicit_slug_conflict_rejected(client, make_admin, fetch_csrf):
    token = await login_admin(client, make_admin, fetch_csrf)
    a = await create_client(client, token, name="A")
    b = await create_client(client, token, name="B")
    res = await client.patch(
        f"/api/clients/{b['id']}",
        json={"slug": a["slug"]},
        headers={"X-CSRF-Token": token},
    )
    assert res.status_code == 409


async def test_media_references_validated(client, make_admin, fetch_csrf):
    token = await login_admin(client, make_admin, fetch_csrf)
    res = await client.post(
        "/api/clients",
        json={"name": "Bad", "logo_media_id": "000000000000000000000000"},
        headers={"X-CSRF-Token": token},
    )
    assert res.status_code == 400
    assert res.json()["error"]["code"] == "INVALID_MEDIA_REFERENCE"

    media = await upload_media(client, token)
    created = await create_client(client, token, name="Good", featured_image_media_id=media["id"])
    assert created["featured_image_media_id"] == media["id"]


# --------------------------------------------------------------------------
# delete / referential integrity
# --------------------------------------------------------------------------
async def test_editor_cannot_delete(client, make_admin, fetch_csrf):
    owner = await login_admin(client, make_admin, fetch_csrf, role=Role.OWNER)
    created = await create_client(client, owner, name="Keep Me")
    editor = await login_admin(
        client, make_admin, fetch_csrf,
        email="editor@example.com", role=Role.EDITOR,
    )
    res = await client.delete(f"/api/clients/{created['id']}", headers={"X-CSRF-Token": editor})
    assert res.status_code == 403
    assert res.json()["error"]["code"] == "INSUFFICIENT_ROLE"
    assert (await client.get(f"/api/clients/{created['id']}")).status_code == 200


async def test_admin_can_delete_and_delete_blocked_when_referenced(client, make_admin, fetch_csrf):
    token = await login_admin(client, make_admin, fetch_csrf, role=Role.OWNER)
    media = await upload_media(client, token)
    client_a = await create_client(client, token, name="Referenced By Project")
    project = await create_project(client, token, name="Proj", client_id=client_a["id"],
                                   thumbnail_media_id=media["id"])
    res = await client.delete(f"/api/clients/{client_a['id']}", headers={"X-CSRF-Token": token})
    assert res.status_code == 409
    body = res.json()["error"]
    assert body["code"] == "CLIENT_IN_USE"
    assert "1 project" in body["message"]
    # project survives (no cascade)
    assert (await client.get(f"/api/projects/{project['id']}")).status_code == 200

    client_b = await create_client(client, token, name="Referenced By Testimonial")
    await create_testimonial(client, token, person_name="P", client_id=client_b["id"])
    res = await client.delete(f"/api/clients/{client_b['id']}", headers={"X-CSRF-Token": token})
    assert res.status_code == 409

    client_c = await create_client(client, token, name="Unreferenced")
    res = await client.delete(f"/api/clients/{client_c['id']}", headers={"X-CSRF-Token": token})
    assert res.status_code == 200
    assert (await client.get(f"/api/clients/{client_c['id']}")).status_code == 404


async def test_delete_requires_csrf(client, make_admin, fetch_csrf):
    token = await login_admin(client, make_admin, fetch_csrf)
    created = await create_client(client, token, name="Tmp")
    res = await client.delete(f"/api/clients/{created['id']}")
    assert res.status_code == 403 and res.json()["error"]["code"] == "CSRF_MISSING"


# --------------------------------------------------------------------------
# public API
# --------------------------------------------------------------------------
async def test_public_list_and_detail(client, make_admin, fetch_csrf):
    token = await login_admin(client, make_admin, fetch_csrf)
    await create_client(client, token, name="Acme Motors", website="https://acme.example", featured=True)
    res = await client.get("/api/public/clients")
    assert res.status_code == 200
    items = res.json()["items"]
    item = items[0]
    assert item["slug"] == "acme-motors"
    assert item["website"] == "https://acme.example"
    assert "id" not in item
    detail = await client.get("/api/public/clients/acme-motors")
    assert detail.status_code == 200
    assert detail.json()["name"] == "Acme Motors"
    assert detail.json()["projects"] == []
    missing = await client.get("/api/public/clients/does-not-exist")
    assert missing.status_code == 404


async def test_public_embeds_only_published_projects(client, make_admin, fetch_csrf):
    token = await login_admin(client, make_admin, fetch_csrf)
    client_a = await create_client(client, token, name="Studio")
    await create_project(client, token, name="Published Proj", client_id=client_a["id"], status="published")
    await create_project(client, token, name="Draft Proj", client_id=client_a["id"], status="draft")
    await create_project(client, token, name="Archived Proj", client_id=client_a["id"], status="archived")
    detail = await client.get(f"/api/public/clients/{client_a['slug']}")
    slugs = [p["slug"] for p in detail.json()["projects"]]
    assert slugs == ["published-proj"]