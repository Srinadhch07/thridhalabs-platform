"""Testimonial moderation tests: public submission, pending invisibility,
approve/reject flow, moderation-field stripping, legacy-doc fallback."""

from __future__ import annotations

from app.db.mongo import get_mongo
from app.models.testimonial import TestimonialStatus as ModerationStatus

from tests._content_helpers import (
    create_testimonial,
    login_admin,
)


async def test_public_submit_lands_pending_and_hidden(client):
    res = await client.post(
        "/api/public/testimonials",
        json={
            "person_name": "Pat Visitor",
            "role": "Founder",
            "company": "Visitor Inc",
            "testimonial_text": "Great lab, would visit again.",
            "rating": 5,
        },
    )
    assert res.status_code == 201, res.text
    assert "awaiting approval" in res.json()["message"]

    stored = await get_mongo().database["testimonials"].find_one(
        {"person_name": "Pat Visitor"}
    )
    assert stored is not None
    assert stored["status"] == ModerationStatus.PENDING.value
    assert stored["published"] is False
    assert stored["featured"] is False

    listed = await client.get("/api/public/testimonials")
    assert listed.status_code == 200
    assert all(t["person_name"] != "Pat Visitor" for t in listed.json()["items"])

    detail = await client.get(f"/api/public/testimonials/{stored['_id']}")
    assert detail.status_code == 404


async def test_public_submit_ignores_moderation_fields(client):
    res = await client.post(
        "/api/public/testimonials",
        json={
            "person_name": "Sneaky",
            "testimonial_text": "Let me in.",
            "published": True,
            "status": "approved",
            "featured": True,
            "display_order": 99,
            "client_id": "000000000000000000000000",
        },
    )
    assert res.status_code == 201, res.text
    stored = await get_mongo().database["testimonials"].find_one({"person_name": "Sneaky"})
    assert stored["status"] == ModerationStatus.PENDING.value
    assert stored["published"] is False
    assert stored["featured"] is False


async def test_approve_makes_public_reject_hides(client, make_admin, fetch_csrf):
    token = await login_admin(client, make_admin, fetch_csrf)
    await client.post(
        "/api/public/testimonials",
        json={"person_name": "Wanda", "testimonial_text": "Approve me please."},
    )
    target = await get_mongo().database["testimonials"].find_one({"person_name": "Wanda"})

    approved = await client.patch(
        f"/api/testimonials/{target['_id']}",
        json={"status": "approved"},
        headers={"X-CSRF-Token": token},
    )
    assert approved.status_code == 200, approved.text
    assert approved.json()["status"] == "approved"
    assert approved.json()["published"] is True

    visible = await client.get("/api/public/testimonials")
    assert any(t["person_name"] == "Wanda" for t in visible.json()["items"])
    detail = await client.get(f"/api/public/testimonials/{target['_id']}")
    assert detail.status_code == 200

    rejected = await client.patch(
        f"/api/testimonials/{target['_id']}",
        json={"status": "rejected"},
        headers={"X-CSRF-Token": token},
    )
    assert rejected.status_code == 200, rejected.text
    assert rejected.json()["status"] == "rejected"
    assert rejected.json()["published"] is False

    hidden = await client.get("/api/public/testimonials")
    assert all(t["person_name"] != "Wanda" for t in hidden.json()["items"])
    assert (await client.get(f"/api/public/testimonials/{target['_id']}")).status_code == 404


async def test_admin_list_status_filter_and_moderation_auth(client, make_admin, fetch_csrf):
    # Moderation surfaces require authentication (fresh client, no session).
    csrf = await fetch_csrf()
    assert (await client.get("/api/testimonials?status=pending")).status_code == 401
    assert (
        await client.patch(
            "/api/testimonials/000000000000000000000000",
            json={"status": "approved"},
            headers={"X-CSRF-Token": csrf},
        )
    ).status_code == 401

    token = await login_admin(client, make_admin, fetch_csrf)
    await client.post(
        "/api/public/testimonials",
        json={"person_name": "Pending Pam", "testimonial_text": "Waiting."},
    )
    await create_testimonial(client, token, person_name="Pub Polly", published=True)

    pending = await client.get("/api/testimonials?status=pending")
    assert pending.status_code == 200
    assert {t["person_name"] for t in pending.json()["items"]} == {"Pending Pam"}

    approved = await client.get("/api/testimonials?status=approved")
    assert {t["person_name"] for t in approved.json()["items"]} == {"Pub Polly"}


async def test_legacy_published_doc_without_status_stays_visible(client, make_admin, fetch_csrf):
    token = await login_admin(client, make_admin, fetch_csrf)
    created = await create_testimonial(client, token, person_name="Legacy Len", published=True)
    await get_mongo().database["testimonials"].update_one(
        {"person_name": "Legacy Len"}, {"$unset": {"status": ""}}
    )

    visible = await client.get("/api/public/testimonials")
    assert any(t["person_name"] == "Legacy Len" for t in visible.json()["items"])
    detail = await client.get(f"/api/public/testimonials/{created['id']}")
    assert detail.status_code == 200

    # And the admin read path reports the derived status.
    admin_view = await client.get(f"/api/testimonials/{created['id']}")
    assert admin_view.json()["status"] == "approved"


async def test_admin_create_published_implies_approved(client, make_admin, fetch_csrf):
    token = await login_admin(client, make_admin, fetch_csrf)
    created = await create_testimonial(client, token, person_name="Direct Dan", published=True)
    assert created["status"] == "approved"
    assert created["published"] is True
    visible = await client.get("/api/public/testimonials")
    assert any(t["person_name"] == "Direct Dan" for t in visible.json()["items"])
