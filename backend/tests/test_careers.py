"""Careers API tests — settings singleton, opportunity CRUD, public rules."""

from __future__ import annotations

from tests._content_helpers import (
    create_opportunity,
    enable_careers,
    login_admin,
)

_PUBLIC_SETTINGS_KEYS = {"enabled", "heading", "description", "application_template"}
_PUBLIC_OPPORTUNITY_KEYS = {
    "slug", "title", "type", "custom_type", "description",
    "skills", "work_mode", "application_email",
}


async def enable_careers_full(client, token: str, **overrides) -> dict:
    payload = {
        "enabled": True,
        "heading": "Join the lab",
        "description": "Open roles in the lab.",
        "application_email": "apply@thridhalabs.com",
        "application_template": "Tell us about yourself.",
    }
    payload.update(overrides)
    res = await client.put("/api/careers", json=payload, headers={"X-CSRF-Token": token})
    assert res.status_code == 200, res.text
    return res.json()


async def open_opportunity(client, token: str, **overrides) -> dict:
    return await create_opportunity(client, token, status="open", **overrides)


async def test_careers_disabled_by_default(client):
    res = await client.get("/api/public/careers/settings")
    assert res.status_code == 200, res.text
    body = res.json()
    assert set(body) == _PUBLIC_SETTINGS_KEYS
    assert body["enabled"] is False
    assert body["heading"] is None
    assert body["description"] is None
    assert body["application_template"] is None


async def test_careers_opportunities_404_when_disabled(client, make_admin, fetch_csrf):
    token = await login_admin(client, make_admin, fetch_csrf)
    await create_opportunity(client, token, status="open")
    res = await client.get("/api/public/careers/opportunities")
    assert res.status_code == 404, res.text
    assert res.json()["error"]["code"] == "CAREERS_NOT_AVAILABLE"


async def test_admin_settings_require_authentication(client):
    res = await client.get("/api/careers")
    assert res.status_code == 401


async def test_admin_can_enable_and_disable(client, make_admin, fetch_csrf):
    token = await login_admin(client, make_admin, fetch_csrf)
    enabled = await enable_careers_full(client, token)
    assert enabled["enabled"] is True
    assert enabled["heading"] == "Join the lab"
    assert enabled["application_email"] == "apply@thridhalabs.com"
    assert "id" in enabled and "created_at" in enabled and "updated_at" in enabled

    disabled = await client.put(
        "/api/careers", json={"enabled": False}, headers={"X-CSRF-Token": token}
    )
    assert disabled.status_code == 200, disabled.text
    assert disabled.json()["enabled"] is False


async def test_admin_settings_require_csrf(client, make_admin, fetch_csrf):
    await login_admin(client, make_admin, fetch_csrf)
    res = await client.put("/api/careers", json={"enabled": True})
    assert res.status_code == 403


async def test_editor_can_write_but_not_delete(client, make_admin, fetch_csrf):
    token = await login_admin(client, make_admin, fetch_csrf)
    opp = await open_opportunity(client, token)
    editor_token = await login_admin(
        client, make_admin, fetch_csrf, email="editor@example.com", role="editor"
    )
    updated = await client.patch(
        f"/api/careers/opportunities/{opp['id']}",
        json={"status": "open"},
        headers={"X-CSRF-Token": editor_token},
    )
    assert updated.status_code == 200, updated.text
    deleted = await client.delete(
        f"/api/careers/opportunities/{opp['id']}",
        headers={"X-CSRF-Token": editor_token},
    )
    assert deleted.status_code == 403


async def test_unauth_write_without_csrf_yields_403(client):
    res = await client.post("/api/careers/opportunities", json={"title": "x", "type": "lab-member"})
    assert res.status_code == 403
    assert res.json()["error"]["code"] == "CSRF_MISSING"


async def test_unauth_admin_requests_rejected(client, fetch_csrf):
    token = await fetch_csrf()  # CSRF passes; auth must still fail
    assert (await client.get("/api/careers")).status_code == 401
    assert (await client.get("/api/careers/opportunities")).status_code == 401
    res = await client.post(
        "/api/careers/opportunities",
        json={"title": "x", "type": "lab-member"},
        headers={"X-CSRF-Token": token},
    )
    assert res.status_code == 401


async def test_required_fields_validated(client, make_admin, fetch_csrf):
    token = await login_admin(client, make_admin, fetch_csrf)
    for payload in (
        {"type": "lab-member", "description": "desc"},
        {"title": "Lab Member", "description": "desc"},
        {"title": "Lab Member", "type": "lab-member"},
    ):
        res = await client.post(
            "/api/careers/opportunities", json=payload, headers={"X-CSRF-Token": token}
        )
        assert res.status_code == 422, res.text


async def test_invalid_application_email_rejected(client, make_admin, fetch_csrf):
    token = await login_admin(client, make_admin, fetch_csrf)
    res = await client.put(
        "/api/careers",
        json={"enabled": True, "application_email": "not-an-email"},
        headers={"X-CSRF-Token": token},
    )
    assert res.status_code == 422, res.text
    res = await client.post(
        "/api/careers/opportunities",
        json={
            "title": "Lab Member",
            "type": "lab-member",
            "description": "desc",
            "application_email": "not-an-email",
        },
        headers={"X-CSRF-Token": token},
    )
    assert res.status_code == 422


async def test_slug_generation_and_collisions(client, make_admin, fetch_csrf):
    token = await login_admin(client, make_admin, fetch_csrf)
    first = await create_opportunity(client, token, title="Machine Learning")
    assert first["slug"] == "machine-learning"
    second = await create_opportunity(client, token, title="Machine Learning")
    assert second["slug"] == "machine-learning-2"

    collision = await client.post(
        "/api/careers/opportunities",
        json={"title": "Other", "type": "lab-member", "description": "x", "slug": "machine-learning"},
        headers={"X-CSRF-Token": token},
    )
    assert collision.status_code == 409
    assert collision.json()["error"]["code"] == "SLUG_TAKEN"

    invalid = await client.post(
        "/api/careers/opportunities",
        json={"title": "Other", "type": "lab-member", "description": "x", "slug": "BAD SLUG"},
        headers={"X-CSRF-Token": token},
    )
    assert invalid.status_code == 422


async def test_opportunity_crud_roundtrip(client, make_admin, fetch_csrf):
    token = await login_admin(client, make_admin, fetch_csrf)
    created = await create_opportunity(
        client,
        token,
        title="Lab Member",
        description="Build things.",
        skills=["Python", "FastAPI"],
        work_mode="remote",
        display_order=2,
    )
    opp_id = created["id"]
    assert created["status"] == "draft"
    assert created["work_mode"] == "remote"
    assert created["display_order"] == 2

    fetched = await client.get(f"/api/careers/opportunities/{opp_id}")
    assert fetched.status_code == 200, fetched.text
    assert fetched.json()["title"] == "Lab Member"

    listed = await client.get("/api/careers/opportunities")
    assert listed.status_code == 200
    assert listed.json()["total"] == 1
    assert listed.json()["items"][0]["id"] == opp_id

    updated = await client.patch(
        f"/api/careers/opportunities/{opp_id}",
        json={"status": "open", "work_mode": "on-site"},
        headers={"X-CSRF-Token": token},
    )
    assert updated.status_code == 200, updated.text
    assert updated.json()["status"] == "open"
    assert updated.json()["work_mode"] == "on-site"

    deleted = await client.delete(
        f"/api/careers/opportunities/{opp_id}", headers={"X-CSRF-Token": token}
    )
    assert deleted.status_code == 200
    gone = await client.get(f"/api/careers/opportunities/{opp_id}")
    assert gone.status_code == 404


async def test_unknown_opportunity_id_returns_404(client, make_admin, fetch_csrf):
    token = await login_admin(client, make_admin, fetch_csrf)
    res = await client.get("/api/careers/opportunities/not-a-real-id")
    assert res.status_code == 404
    res = await client.get("/api/careers/opportunities/507f1f77bcf86cd799439011")
    assert res.status_code == 404


async def test_opportunity_mutations_require_csrf(client, make_admin, fetch_csrf):
    token = await login_admin(client, make_admin, fetch_csrf)
    opp = await create_opportunity(client, token)
    res = await client.patch(
        f"/api/careers/opportunities/{opp['id']}", json={"status": "open"}
    )
    assert res.status_code == 403
    res = await client.delete(f"/api/careers/opportunities/{opp['id']}")
    assert res.status_code == 403


async def test_custom_type_required_for_other(client, make_admin, fetch_csrf):
    token = await login_admin(client, make_admin, fetch_csrf)
    missing = await client.post(
        "/api/careers/opportunities",
        json={"title": "Residency", "type": "other", "description": "x"},
        headers={"X-CSRF-Token": token},
    )
    assert missing.status_code == 422

    created = await create_opportunity(
        client, token, title="Residency", type="other", custom_type="Residency"
    )
    assert created["custom_type"] == "Residency"

    switched = await client.patch(
        f"/api/careers/opportunities/{created['id']}",
        json={"type": "lab-member"},
        headers={"X-CSRF-Token": token},
    )
    assert switched.status_code == 200
    assert switched.json()["custom_type"] is None


async def test_custom_type_not_stored_for_non_other(client, make_admin, fetch_csrf):
    token = await login_admin(client, make_admin, fetch_csrf)
    created = await create_opportunity(
        client, token, title="Lab Member", type="lab-member", custom_type="ignored"
    )
    assert created["custom_type"] is None


async def test_drafts_and_closed_not_public(client, make_admin, fetch_csrf):
    token = await login_admin(client, make_admin, fetch_csrf)
    await enable_careers(client, token)
    await open_opportunity(client, token, title="Open Role")
    await create_opportunity(client, token, title="Draft Role")
    await create_opportunity(client, token, title="Closed Role", status="closed")

    res = await client.get("/api/public/careers/opportunities")
    assert res.status_code == 200, res.text
    body = res.json()
    titles = [item["title"] for item in body["items"]]
    assert titles == ["Open Role"]
    assert body["total"] == 1


async def test_open_opportunities_only_when_enabled(client, make_admin, fetch_csrf):
    token = await login_admin(client, make_admin, fetch_csrf)
    await open_opportunity(client, token, title="Open Role")

    off = await client.get("/api/public/careers/opportunities")
    assert off.status_code == 404

    await enable_careers(client, token)
    on = await client.get("/api/public/careers/opportunities")
    assert on.status_code == 200
    assert on.json()["total"] == 1

    await client.put("/api/careers", json={"enabled": False}, headers={"X-CSRF-Token": token})
    again = await client.get("/api/public/careers/opportunities")
    assert again.status_code == 404


async def test_disabled_settings_not_exposed(client, make_admin, fetch_csrf):
    token = await login_admin(client, make_admin, fetch_csrf)
    await enable_careers_full(
        client,
        token,
        heading="Secret heading",
        description="Secret description",
        application_email="secret@example.com",
        application_template="Secret template",
    )

    while_enabled = await client.get("/api/public/careers/settings")
    assert while_enabled.json()["heading"] == "Secret heading"
    assert while_enabled.json()["application_template"] == "Secret template"

    await client.put("/api/careers", json={"enabled": False}, headers={"X-CSRF-Token": token})
    while_disabled = await client.get("/api/public/careers/settings")
    body = while_disabled.json()
    assert set(body) == _PUBLIC_SETTINGS_KEYS
    assert body["enabled"] is False
    assert body["heading"] is None
    assert body["application_template"] is None


async def test_public_response_exposes_only_intended_fields(client, make_admin, fetch_csrf):
    token = await login_admin(client, make_admin, fetch_csrf)
    await enable_careers(client, token)
    await open_opportunity(client, token)
    res = await client.get("/api/public/careers/opportunities")
    assert res.status_code == 200
    body = res.json()
    assert set(body) == {"items", "total", "page", "page_size", "pages"}
    assert set(body["items"][0]) == _PUBLIC_OPPORTUNITY_KEYS
    assert "id" not in body["items"][0]
    assert "status" not in body["items"][0]


async def test_email_override_and_default_resolution(client, make_admin, fetch_csrf):
    token = await login_admin(client, make_admin, fetch_csrf)
    await enable_careers_full(client, token, application_email="default@example.com")
    await open_opportunity(client, token, title="Uses Default")
    await open_opportunity(client, token, title="Overrides", application_email="override@example.com")

    res = await client.get("/api/public/careers/opportunities")
    by_title = {item["title"]: item for item in res.json()["items"]}
    assert by_title["Uses Default"]["application_email"] == "default@example.com"
    assert by_title["Overrides"]["application_email"] == "override@example.com"


async def test_missing_email_is_null_and_safe(client, make_admin, fetch_csrf):
    token = await login_admin(client, make_admin, fetch_csrf)
    await enable_careers(client, token)
    await open_opportunity(client, token, title="No Email")
    res = await client.get("/api/public/careers/opportunities")
    assert res.json()["items"][0]["application_email"] is None


async def test_admin_list_filters_and_pagination(client, make_admin, fetch_csrf):
    token = await login_admin(client, make_admin, fetch_csrf)
    await create_opportunity(client, token, title="A", status="draft")
    await create_opportunity(client, token, title="B", status="open")
    await create_opportunity(client, token, title="C", status="open")

    listed = await client.get("/api/careers/opportunities?page_size=2")
    assert listed.status_code == 200
    assert listed.json()["total"] == 3
    assert listed.json()["pages"] == 2
    assert len(listed.json()["items"]) == 2

    open_only = await client.get("/api/careers/opportunities?status=open")
    assert open_only.json()["total"] == 2

    type_filter = await client.get("/api/careers/opportunities?type=lab-member")
    assert type_filter.json()["total"] == 3


async def test_invalid_sort_rejected(client, make_admin, fetch_csrf):
    token = await login_admin(client, make_admin, fetch_csrf)
    res = await client.get("/api/careers/opportunities?sort=application_email")
    assert res.status_code == 422
    assert res.json()["error"]["code"] == "INVALID_SORT"