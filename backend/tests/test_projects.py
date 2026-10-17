"""Projects API tests: CRUD, slugs, statuses/types, media & client references,
pagination/filters/sorting, public published-only behavior, RBAC/CSRF."""

from __future__ import annotations

from app.models.admin import Role

from tests._content_helpers import (
    create_client,
    create_project,
    login_admin,
    upload_media,
)


async def test_create_with_default_draft(client, make_admin, fetch_csrf):
    token = await login_admin(client, make_admin, fetch_csrf)
    created = await create_project(client, token, name="My Product")
    assert created["slug"] == "my-product"
    assert created["status"] == "draft"
    assert created["project_type"] == "product"


async def test_create_explicit_slug_and_status(client, make_admin, fetch_csrf):
    token = await login_admin(client, make_admin, fetch_csrf)
    res = await client.post(
        "/api/projects",
        json={"name": "X", "slug": "x-special", "status": "published", "project_type": "client-work"},
        headers={"X-CSRF-Token": token},
    )
    assert res.status_code == 201
    assert res.json()["slug"] == "x-special"
    assert res.json()["status"] == "published"


async def test_validation_of_required_and_enum_fields(client, make_admin, fetch_csrf):
    token = await login_admin(client, make_admin, fetch_csrf)
    cases = [
        {"name": "No type"},
        {"name": "Bad status", "project_type": "product", "status": "secret-stash"},
        {"name": "Bad type", "project_type": "money-maker"},
        {"name": "X", "project_type": "product", "live_url": "ftp://nope.example"},
    ]
    for payload in cases:
        res = await client.post(
            "/api/projects", json=payload, headers={"X-CSRF-Token": token}
        )
        assert res.status_code == 422, (payload, res.text)


async def test_duplicate_slug_rejected_and_suffix_path(client, make_admin, fetch_csrf):
    token = await login_admin(client, make_admin, fetch_csrf)
    await create_project(client, token, name="Dup Proj")
    second = await create_project(client, token, name="Dup Proj")
    assert second["slug"] == "dup-proj-2"
    res = await client.post(
        "/api/projects",
        json={"name": "Other", "slug": "dup-proj", "project_type": "product"},
        headers={"X-CSRF-Token": token},
    )
    assert res.status_code == 409


async def test_client_reference_validated(client, make_admin, fetch_csrf):
    token = await login_admin(client, make_admin, fetch_csrf)
    res = await client.post(
        "/api/projects",
        json={"name": "No Client", "project_type": "product", "client_id": "000000000000000000000000"},
        headers={"X-CSRF-Token": token},
    )
    assert res.status_code == 400
    assert res.json()["error"]["code"] == "INVALID_CLIENT_REFERENCE"

    client_doc = await create_client(client, token, name="Real Client")
    proj = await create_project(client, token, name="With Client", client_id=client_doc["id"])
    assert proj["client"]["slug"] == "real-client"
    assert proj["client"]["name"] == "Real Client"


async def test_media_references_validated(client, make_admin, fetch_csrf):
    token = await login_admin(client, make_admin, fetch_csrf)
    res = await client.post(
        "/api/projects",
        json={
            "name": "Bad Media", "project_type": "product",
            "thumbnail_media_id": "000000000000000000000000",
            "gallery_media_ids": ["000000000000000000000001"],
        },
        headers={"X-CSRF-Token": token},
    )
    assert res.status_code == 400
    assert res.json()["error"]["code"] == "INVALID_MEDIA_REFERENCE"

    media = await upload_media(client, token)
    ok = await create_project(
        client, token, name="Good Media",
        thumbnail_media_id=media["id"], gallery_media_ids=[media["id"]],
    )
    assert ok["thumbnail_media_id"] == media["id"]
    assert ok["gallery_media_ids"] == [media["id"]]


async def test_list_filters_and_sorting(client, make_admin, fetch_csrf):
    token = await login_admin(client, make_admin, fetch_csrf)
    await create_project(client, token, name="Web App", project_type="client-work",
                         status="published", category="web", featured=True, display_order=1)
    await create_project(client, token, name="Fun App", project_type="experiment",
                         status="draft", category="fun", display_order=0)
    await create_project(client, token, name="Tool", project_type="product",
                         status="published", category="web", display_order=2)

    r = await client.get("/api/projects?status=published")
    assert r.json()["total"] == 2
    r = await client.get("/api/projects?project_type=experiment")
    assert r.json()["total"] == 1
    r = await client.get("/api/projects?category=web")
    assert r.json()["total"] == 2
    r = await client.get("/api/projects?featured=true")
    assert r.json()["total"] == 1

    r = await client.get("/api/projects?sort=display_order&order=asc")
    names = [p["name"] for p in r.json()["items"]]
    assert names == ["Fun App", "Web App", "Tool"]

    r = await client.get("/api/projects?page=1&page_size=2&sort=created_at")
    assert len(r.json()["items"]) == 2 and r.json()["total"] == 3

    bad = await client.get("/api/projects?sort=__proto__")
    assert bad.status_code == 422


async def test_patch_keeps_slug_and_updates(client, make_admin, fetch_csrf):
    token = await login_admin(client, make_admin, fetch_csrf)
    created = await create_project(client, token, name="V1", project_type="product")
    res = await client.patch(
        f"/api/projects/{created['id']}",
        json={"name": "V2", "status": "published"},
        headers={"X-CSRF-Token": token},
    )
    assert res.status_code == 200
    body = res.json()
    assert body["name"] == "V2"
    assert body["slug"] == "v1"  # unchanged
    assert body["status"] == "published"


async def test_patch_slug_conflict_rejected(client, make_admin, fetch_csrf):
    token = await login_admin(client, make_admin, fetch_csrf)
    a = await create_project(client, token, name="A", project_type="product")
    b = await create_project(client, token, name="B", project_type="product")
    res = await client.patch(
        f"/api/projects/{b['id']}", json={"slug": "a"}, headers={"X-CSRF-Token": token}
    )
    assert res.status_code == 409


async def test_rbac_and_csrf(client, make_admin, fetch_csrf):
    token = await login_admin(client, make_admin, fetch_csrf, role=Role.EDITOR)
    created = await create_project(client, token, name="Edit Me", project_type="product")
    assert (await client.get("/api/projects")).status_code == 200  # editor may read
    res = await client.delete(f"/api/projects/{created['id']}")
    assert res.status_code == 403 and res.json()["error"]["code"] == "CSRF_MISSING"
    res = await client.delete(f"/api/projects/{created['id']}", headers={"X-CSRF-Token": token})
    assert res.status_code == 403 and res.json()["error"]["code"] == "INSUFFICIENT_ROLE"

    owner = await login_admin(client, make_admin, fetch_csrf, email="owner2@example.com", role=Role.OWNER)
    res = await client.delete(f"/api/projects/{created['id']}", headers={"X-CSRF-Token": owner})
    assert res.status_code == 200


async def test_unauth_admin_requests_rejected(client, fetch_csrf):
    token = await fetch_csrf()  # CSRF passes; auth must still fail
    assert (await client.get("/api/projects")).status_code == 401
    assert (await client.post("/api/projects", json={}, headers={"X-CSRF-Token": token})).status_code == 401


# --------------------------------------------------------------------------
# public API
# --------------------------------------------------------------------------
async def test_public_shows_only_published(client, make_admin, fetch_csrf):
    token = await login_admin(client, make_admin, fetch_csrf)
    await create_project(client, token, name="Shown", project_type="product", status="published", featured=True)
    await create_project(client, token, name="Hidden Draft", project_type="product", status="draft")
    await create_project(client, token, name="Hidden Archived", project_type="product", status="archived")

    res = await client.get("/api/public/projects")
    assert res.status_code == 200
    items = res.json()["items"]
    assert len(items) == 1
    assert items[0]["slug"] == "shown"
    assert "id" not in items[0]
    assert "client_id" not in items[0]

    hidden = await client.get("/api/public/projects/hidden-draft")
    assert hidden.status_code == 404
    archived = await client.get("/api/public/projects/hidden-archived")
    assert archived.status_code == 404
    shown = await client.get("/api/public/projects/shown")
    assert shown.status_code == 200


async def test_public_filters(client, make_admin, fetch_csrf):
    token = await login_admin(client, make_admin, fetch_csrf)
    await create_project(client, token, name="Client Work", project_type="client-work", status="published", category="web")
    await create_project(client, token, name="Experiment", project_type="experiment", status="published", featured=True)

    r = await client.get("/api/public/projects?project_type=client-work")
    assert [p["name"] for p in r.json()["items"]] == ["Client Work"]
    r = await client.get("/api/public/projects?featured=true")
    assert [p["name"] for p in r.json()["items"]] == ["Experiment"]
    r = await client.get("/api/public/projects?category=web")
    assert r.json()["total"] == 1


async def test_completion_date_round_trips_as_iso_date_string(client, make_admin, fetch_csrf):
    """Regression: `completion_date` is a date-only field — it must survive
    the Mongo round-trip as `YYYY-MM-DD` on create, fetch and patch."""
    token = await login_admin(client, make_admin, fetch_csrf)
    created = await create_project(client, token, name="Dated", completion_date="2025-11-21")
    assert created["completion_date"] == "2025-11-21"

    fetched = await client.get(f"/api/projects/{created['id']}")
    assert fetched.status_code == 200
    assert fetched.json()["completion_date"] == "2025-11-21"

    patched = await client.patch(
        f"/api/projects/{created['id']}",
        json={"completion_date": "2025-11-22"},
        headers={"X-CSRF-Token": token},
    )
    assert patched.status_code == 200, patched.text
    assert patched.json()["completion_date"] == "2025-11-22"