"""Activity management tests (Phase 1).

Covers RBAC + CSRF, lifecycle + derived presentation labels, public visibility
(drafts archived never listed; cancelled reachable but never promoted), PDF brief
validation/versioning, project invitations + emails, manual confirmation, and
duplicate-safe open self-registration with withdraw/re-register.
"""

from __future__ import annotations

from datetime import date, datetime, timedelta, timezone

import pytest
from httpx import ASGITransport, AsyncClient

from app.core.config import get_settings
from app.main import app
from app.models.admin import Role
from tests._content_helpers import (
    capture_activity_emails,
    capture_onboarding_token,
    create_activity,
    create_member,
    invite_to_activity,
    list_activity_participants,
    login_admin,
    onboard_member,
    patch_activity,
    pdf_bytes,
    publish_activity,
    register_activity,
    update_participant,
    upload_activity_brief,
    upload_media,
    withdraw_activity,
)


def _second_client() -> AsyncClient:
    return AsyncClient(transport=ASGITransport(app=app), base_url="https://testserver")


def _today() -> date:
    return datetime.now(timezone.utc).date()


def _future(days: int) -> str:
    return (_today() + timedelta(days=days)).isoformat()


def _past(days: int) -> str:
    return (_today() - timedelta(days=days)).isoformat()


async def _onboard(monkeypatch, admin_client, admin_token, email: str):
    member_client = _second_client()
    capture = capture_onboarding_token(monkeypatch)
    readable, token = await onboard_member(
        member_client, admin_client, admin_token, capture, email=email
    )
    return member_client, readable, token


# ---------------------------------------------------------------------------
# RBAC / CSRF
# ---------------------------------------------------------------------------
async def test_create_requires_authentication(client, fetch_csrf):
    token = await fetch_csrf()
    res = await client.post(
        "/api/admin/activities",
        json={"title": "X", "activity_type": "programme"},
        headers={"X-CSRF-Token": token},
    )
    assert res.status_code == 401, res.text


async def test_create_requires_csrf(client, make_admin, fetch_csrf):
    await login_admin(client, make_admin, fetch_csrf)
    res = await client.post(
        "/api/admin/activities", json={"title": "X", "activity_type": "programme"}
    )
    assert res.status_code == 403, res.text


async def test_delete_requires_admin_role(client, make_admin, fetch_csrf):
    token = await login_admin(client, make_admin, fetch_csrf, role=Role.EDITOR)
    created = await create_activity(client, token, title="Editor Made")
    res = await client.delete(
        f"/api/admin/activities/{created['id']}", headers={"X-CSRF-Token": token}
    )
    assert res.status_code == 403, res.text


# ---------------------------------------------------------------------------
# Public visibility + lifecycle
# ---------------------------------------------------------------------------
async def test_draft_is_never_public(client, make_admin, fetch_csrf):
    token = await login_admin(client, make_admin, fetch_csrf)
    draft = await create_activity(client, token, title="Hidden Draft")

    listing = await client.get("/api/public/activities")
    assert listing.status_code == 200
    assert all(item["slug"] != draft["slug"] for item in listing.json()["items"])

    detail = await client.get(f"/api/public/activities/{draft['slug']}")
    assert detail.status_code == 404, detail.text


async def test_publish_then_cancel_and_archive(client, make_admin, fetch_csrf):
    token = await login_admin(client, make_admin, fetch_csrf)
    activity = await create_activity(client, token, title="Solar Hackathon",
                                     activity_type="hackathon")
    await publish_activity(client, token, activity["id"])

    listed = await client.get("/api/public/activities")
    assert any(i["slug"] == activity["slug"] for i in listed.json()["items"])

    # Cancel → detail stays reachable + clearly marked, list no longer shows it.
    status, _ = await patch_activity(client, token, activity["id"], status="cancelled")
    assert status == 200
    detail = await client.get(f"/api/public/activities/{activity['slug']}")
    assert detail.status_code == 200
    assert detail.json()["presentation_status"] == "cancelled"
    listed = await client.get("/api/public/activities")
    assert all(i["slug"] != activity["slug"] for i in listed.json()["items"])

    # Archive → no longer public at all.
    status, _ = await patch_activity(client, token, activity["id"], status="archived")
    assert status == 200
    assert (
        await client.get(f"/api/public/activities/{activity['slug']}")
    ).status_code == 404


@pytest.mark.parametrize(
    "start,end,expected",
    [
        (None, None, "upcoming"),
        (_future(5), _future(10), "upcoming"),
        (_past(2), _future(5), "ongoing"),
        (_past(10), _past(1), "completed"),
    ],
)
async def test_presentation_labels(client, make_admin, fetch_csrf, start, end, expected):
    token = await login_admin(client, make_admin, fetch_csrf)
    body = {"title": "Label Test", "activity_type": "programme", "status": "published"}
    if start:
        body["start_date"] = start
    if end:
        body["end_date"] = end
    activity = await create_activity(client, token, **body)
    detail = await client.get(f"/api/public/activities/{activity['slug']}")
    assert detail.status_code == 200, detail.text
    assert detail.json()["presentation_status"] == expected


async def test_slug_uniqueness_and_auto_suffix(client, make_admin, fetch_csrf):
    token = await login_admin(client, make_admin, fetch_csrf)
    first = await create_activity(client, token, title="Same Title")
    second = await create_activity(client, token, title="Same Title")
    assert first["slug"] != second["slug"]

    res = await client.post(
        "/api/admin/activities",
        json={"title": "Conflict", "activity_type": "programme", "slug": first["slug"]},
        headers={"X-CSRF-Token": token},
    )
    assert res.status_code == 409, res.text


async def test_invalid_date_window_rejected(client, make_admin, fetch_csrf):
    token = await login_admin(client, make_admin, fetch_csrf)
    res = await client.post(
        "/api/admin/activities",
        json={
            "title": "Bad Dates",
            "activity_type": "programme",
            "start_date": _future(10),
            "end_date": _future(1),
        },
        headers={"X-CSRF-Token": token},
    )
    assert res.status_code == 422, res.text


# ---------------------------------------------------------------------------
# PDF brief
# ---------------------------------------------------------------------------
async def test_brief_rejects_non_pdf(client, make_admin, fetch_csrf):
    token = await login_admin(client, make_admin, fetch_csrf)
    activity = await create_activity(client, token, title="Brief Test")
    status, body = await upload_activity_brief(
        client, token, activity["id"], data=b"this is not a pdf"
    )
    assert status == 415, body


async def test_brief_rejects_oversized(client, make_admin, fetch_csrf, monkeypatch):
    token = await login_admin(client, make_admin, fetch_csrf)
    activity = await create_activity(client, token, title="Big Brief")
    monkeypatch.setattr(get_settings(), "ACTIVITY_BRIEF_MAX_BYTES", 1024)
    # The router enforces the streaming ceiling too, so patch it as well.
    monkeypatch.setattr(
        "app.modules.activities.router.get_settings", get_settings
    )
    big = pdf_bytes("x" * 4096)
    status, _ = await upload_activity_brief(client, token, activity["id"], data=big)
    assert status == 413


async def test_brief_versioning_and_public_download(client, make_admin, fetch_csrf):
    token = await login_admin(client, make_admin, fetch_csrf)
    activity = await create_activity(
        client, token, title="Versioned Brief", activity_type="programme"
    )

    status, body = await upload_activity_brief(client, token, activity["id"])
    assert status == 200, body
    assert body["brief"]["version"] == 1
    assert body["brief_history_count"] == 1

    # Replacing appends a version; the previous one is auditable.
    status, body = await upload_activity_brief(
        client, token, activity["id"], data=pdf_bytes("revised")
    )
    assert body["brief"]["version"] == 2
    assert body["brief_history_count"] == 2

    # Draft briefs are never public.
    assert (
        await client.get(f"/api/public/activities/{activity['slug']}/brief")
    ).status_code == 404

    await publish_activity(client, token, activity["id"])
    detail = await client.get(f"/api/public/activities/{activity['slug']}")
    assert detail.json()["has_brief"] is True
    download = await client.get(f"/api/public/activities/{activity['slug']}/brief")
    assert download.status_code == 200
    assert download.content.startswith(b"%PDF-")

    # Removing clears the pointer but keeps the history count.
    res = await client.delete(
        f"/api/admin/activities/{activity['id']}/brief",
        headers={"X-CSRF-Token": token},
    )
    assert res.status_code == 200, res.text
    assert res.json()["brief"] is None
    assert res.json()["brief_history_count"] == 2


async def test_invalid_banner_media_rejected(client, make_admin, fetch_csrf):
    token = await login_admin(client, make_admin, fetch_csrf)
    res = await client.post(
        "/api/admin/activities",
        json={
            "title": "Banner Test",
            "activity_type": "programme",
            "banner_media_id": "000000000000000000000000",
        },
        headers={"X-CSRF-Token": token},
    )
    assert res.status_code == 400, res.text


async def test_featured_carousel_only_published_featured(client, make_admin, fetch_csrf):
    token = await login_admin(client, make_admin, fetch_csrf)
    media = await upload_media(client, token)

    draft = await create_activity(
        client, token, title="Featured Draft", featured=True, banner_media_id=media["id"]
    )
    pub = await create_activity(
        client, token, title="Featured Live", featured=True, banner_media_id=media["id"]
    )
    await publish_activity(client, token, pub["id"])

    res = await client.get("/api/public/activities", params={"featured": True})
    slugs = [i["slug"] for i in res.json()["items"]]
    assert pub["slug"] in slugs
    assert draft["slug"] not in slugs


# ---------------------------------------------------------------------------
# Project invitations + manual confirmation
# ---------------------------------------------------------------------------
async def test_invitations_require_published_project(client, make_admin, fetch_csrf, monkeypatch):
    capture = capture_activity_emails(monkeypatch)
    token = await login_admin(client, make_admin, fetch_csrf)
    capture_onboarding_token(monkeypatch)
    member = await create_member(client, token, email="inv1@example.com")

    draft_project = await create_activity(
        client, token, title="Draft Project", activity_type="project"
    )
    status, body = await invite_to_activity(
        client, token, draft_project["id"], [{"member_id": member["id"]}]
    )
    assert status == 409, body
    assert capture["messages"] == []

    # Open activities never accept invitations either.
    programme = await create_activity(
        client, token, title="Open Programme", activity_type="programme", status="published"
    )
    status, body = await invite_to_activity(
        client, token, programme["id"], [{"member_id": member["id"]}]
    )
    assert status == 409, body


async def test_project_invitation_flow(client, make_admin, fetch_csrf, monkeypatch):
    capture = capture_activity_emails(monkeypatch)
    token = await login_admin(client, make_admin, fetch_csrf)
    capture_onboarding_token(monkeypatch)
    m1 = await create_member(client, token, email="p1@example.com", full_name="Pat One")
    m2 = await create_member(client, token, email="p2@example.com", full_name="Pat Two")

    project = await create_activity(
        client, token, title="Invite Only Project", activity_type="project"
    )
    # Sending an invitation must NOT add a member as a participant.
    await publish_activity(client, token, project["id"])

    status, result = await invite_to_activity(
        client,
        token,
        project["id"],
        [
            {"member_id": m1["id"], "role": "Frontend Developer"},
            {"member_id": m2["id"]},
        ],
    )
    assert status == 200, result
    assert result["invited"] == 2
    assert result["emails_sent"] == 2
    assert len(capture["messages"]) == 2
    assert all("Invite Only Project" in msg["subject"] for msg in capture["messages"])

    participants = await list_activity_participants(client, token, project["id"])
    assert participants["total"] == 2
    assert {p["status"] for p in participants["items"]} == {"invited"}
    by_member = {p["member_readable_id"]: p for p in participants["items"]}
    assert by_member[m1["member_id"]]["role"] == "Frontend Developer"

    # Manual path: record interest, then explicitly confirm.
    p1 = by_member[m1["member_id"]]
    status, body = await update_participant(
        client, token, project["id"], p1["id"], status="interested"
    )
    assert body["status"] == "interested"
    status, body = await update_participant(
        client, token, project["id"], p1["id"], status="confirmed"
    )
    assert body["status"] == "confirmed"
    assert body["confirmed_at"] is not None

    # Re-inviting a confirmed member is skipped, not downgraded.
    before = len(capture["messages"])
    status, result = await invite_to_activity(
        client, token, project["id"], [{"member_id": m1["id"]}, {"member_id": m2["id"]}]
    )
    assert result["re_invited"] == 1
    assert m1["member_id"] in result["skipped"]
    assert len(capture["messages"]) == before + 1  # only m2 re-emailed

    counts = (await client.get(f"/api/admin/activities/{project['id']}")).json()[
        "participant_counts"
    ]
    assert counts.get("confirmed") == 1
    assert counts.get("invited") == 1


async def test_invitation_email_failure_is_reported(
    client, make_admin, fetch_csrf, monkeypatch
):
    token = await login_admin(client, make_admin, fetch_csrf)
    capture_onboarding_token(monkeypatch)
    capture = capture_activity_emails(monkeypatch, fail=True)
    member = await create_member(client, token, email="fail@example.com")

    project = await create_activity(
        client, token, title="Flaky Email Project", activity_type="project"
    )
    await publish_activity(client, token, project["id"])
    status, result = await invite_to_activity(
        client, token, project["id"], [{"member_id": member["id"]}]
    )
    assert status == 200, result
    assert result["invited"] == 1
    assert result["emails_sent"] == 0
    assert result["email_failures"] == 1
    assert capture["messages"] == []


# ---------------------------------------------------------------------------
# Open self-registration (programme / hackathon)
# ---------------------------------------------------------------------------
async def test_open_registration_duplicate_and_withdraw(
    client, make_admin, fetch_csrf, monkeypatch
):
    admin_token = await login_admin(client, make_admin, fetch_csrf)
    programme = await create_activity(
        client, admin_token, title="Open Programme", activity_type="programme"
    )
    await publish_activity(client, admin_token, programme["id"])

    member_client, _readable, mtoken = await _onboard(
        monkeypatch, client, admin_token, "selfreg@example.com"
    )
    try:
        status, body = await register_activity(member_client, mtoken, programme["slug"])
        assert status == 200, body
        assert body["participation_status"] == "confirmed"
        assert body["can_withdraw"] is True

        # Duplicate registration is prevented.
        status, body = await register_activity(member_client, mtoken, programme["slug"])
        assert status == 409, body

        status, body = await withdraw_activity(member_client, mtoken, programme["slug"])
        assert status == 200, body
        assert body["participation_status"] == "withdrawn"
        assert body["can_register"] is True

        # Re-registering after withdrawing is allowed.
        status, body = await register_activity(member_client, mtoken, programme["slug"])
        assert status == 200, body
        assert body["participation_status"] == "confirmed"

        listing = await member_client.get("/api/member/activities")
        assert listing.status_code == 200, listing.text
        entry = next(i for i in listing.json()["items"] if i["slug"] == programme["slug"])
        assert entry["participation_status"] == "confirmed"
    finally:
        await member_client.aclose()


async def test_project_self_registration_forbidden(
    client, make_admin, fetch_csrf, monkeypatch
):
    admin_token = await login_admin(client, make_admin, fetch_csrf)
    project = await create_activity(
        client, admin_token, title="Closed Project", activity_type="project"
    )
    await publish_activity(client, admin_token, project["id"])

    member_client, _readable, mtoken = await _onboard(
        monkeypatch, client, admin_token, "projector@example.com"
    )
    try:
        status, body = await register_activity(member_client, mtoken, project["slug"])
        assert status == 403, body
    finally:
        await member_client.aclose()


async def test_registration_closed_after_end_date(
    client, make_admin, fetch_csrf, monkeypatch
):
    admin_token = await login_admin(client, make_admin, fetch_csrf)
    hackathon = await create_activity(
        client,
        admin_token,
        title="Finished Hackathon",
        activity_type="hackathon",
        status="published",
        start_date=_past(30),
        end_date=_past(1),
    )
    assert hackathon["presentation_status"] == "completed"

    member_client, _readable, mtoken = await _onboard(
        monkeypatch, client, admin_token, "late@example.com"
    )
    try:
        status, body = await register_activity(member_client, mtoken, hackathon["slug"])
        assert status == 409, body
    finally:
        await member_client.aclose()


async def test_registration_requires_authentication(client, make_admin, fetch_csrf):
    admin_token = await login_admin(client, make_admin, fetch_csrf)
    programme = await create_activity(
        client, admin_token, title="Auth Needed", activity_type="programme"
    )
    await publish_activity(client, admin_token, programme["id"])

    csrf = await client.get("/api/member/csrf")
    res = await client.post(
        f"/api/member/activities/{programme['slug']}/register",
        headers={"X-CSRF-Token": csrf.json()["csrfToken"]},
    )
    assert res.status_code == 401, res.text
