"""Project Progress Reports tests.

Covers the confirmed-participant authorization, CSRF + RBAC, validation
(500-char description, http(s) evidence links), idempotent submission,
member-only ownership, edit/resubmit with preserved review history, the admin
review queue (filters + search), and the approved-only contribution history.
"""

from __future__ import annotations

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app
from app.models.admin import Role
from tests._content_helpers import (
    capture_onboarding_token,
    create_activity,
    create_member,
    invite_to_activity,
    list_activity_participants,
    login_admin,
    member_login,
    member_setup,
    publish_activity,
    update_participant,
)


def _second_client() -> AsyncClient:
    return AsyncClient(transport=ASGITransport(app=app), base_url="https://testserver")


async def _confirmed_member(
    client,
    admin_token: str,
    monkeypatch,
    *,
    email: str,
    role: str | None = None,
    title: str = "Report Project",
):
    """Create a member, a published project, invite + explicitly confirm the
    member, and return (member_client, member_csrf, project, member, readable)."""
    capture = capture_onboarding_token(monkeypatch)
    member = await create_member(client, admin_token, email=email, full_name=email.split("@")[0])
    project = await create_activity(client, admin_token, title=title, activity_type="project")
    await publish_activity(client, admin_token, project["id"])

    member_client = _second_client()
    await member_setup(member_client, capture["token"])
    mtoken = await member_login(member_client, email)
    readable = member["member_id"]
    invitation = {"member_id": member["id"]}
    if role:
        invitation["role"] = role
    status, _ = await invite_to_activity(client, admin_token, project["id"], [invitation])
    assert status == 200
    participants = await list_activity_participants(client, admin_token, project["id"])
    p = next(
        item for item in participants["items"] if item["member_readable_id"] == readable
    )
    _, body = await update_participant(
        client, admin_token, project["id"], p["id"], status="confirmed"
    )
    assert body["status"] == "confirmed"
    return member_client, mtoken, project, member, readable


async def _submit(member_client, token, project_id, **overrides):
    payload = {"activity_id": project_id, "description": "Shipped the dashboard."}
    payload.update(overrides)
    res = await member_client.post(
        "/api/member/reports", json=payload, headers={"X-CSRF-Token": token}
    )
    return res.status_code, res.json()


# ---------------------------------------------------------------------------
# Auth / CSRF / authorization
# ---------------------------------------------------------------------------
async def test_submit_requires_authentication(client):
    csrf = await client.get("/api/member/csrf")
    token = csrf.json()["csrfToken"]
    res = await client.post(
        "/api/member/reports",
        json={"activity_id": "x", "description": "nope"},
        headers={"X-CSRF-Token": token},
    )
    assert res.status_code == 401, res.text


async def test_submit_requires_csrf(client, make_admin, fetch_csrf, monkeypatch):
    admin_token = await login_admin(client, make_admin, fetch_csrf)
    member_client, _mtoken, project, _member, _readable = await _confirmed_member(
        client, admin_token, monkeypatch, email="csrf@example.com"
    )
    try:
        res = await member_client.post(
            "/api/member/reports",
            json={"activity_id": project["id"], "description": "No csrf"},
        )
        assert res.status_code == 403, res.text
    finally:
        await member_client.aclose()


async def test_submit_requires_confirmed_participant(
    client, make_admin, fetch_csrf, monkeypatch
):
    admin_token = await login_admin(client, make_admin, fetch_csrf)
    # A member who is NOT a participant (created but never invited).
    capture = capture_onboarding_token(monkeypatch)
    await create_member(client, admin_token, email="outsider@example.com")
    member_client = _second_client()
    await member_setup(member_client, capture["token"])
    mtoken = await member_login(member_client, "outsider@example.com")
    project = await create_activity(
        client, admin_token, title="Members Only", activity_type="project"
    )
    await publish_activity(client, admin_token, project["id"])
    try:
        status, body = await _submit(member_client, mtoken, project["id"])
        assert status == 403, body
        assert body["error"]["code"] == "NOT_A_PARTICIPANT"

        # Unknown project id → 404 (no leak).
        status, body = await _submit(member_client, mtoken, "000000000000000000000000")
        assert status == 404, body

        # A programme id is never a valid report target.
        programme = await create_activity(
            client, admin_token, title="A Programme", activity_type="programme"
        )
        status, body = await _submit(member_client, mtoken, programme["id"])
        assert status == 404, body
    finally:
        await member_client.aclose()


async def test_submit_never_accepts_forged_author(
    client, make_admin, fetch_csrf, monkeypatch
):
    admin_token = await login_admin(client, make_admin, fetch_csrf)
    member_client, mtoken, project, member, readable = await _confirmed_member(
        client, admin_token, monkeypatch, email="author@example.com"
    )
    try:
        # A client-supplied member_id is rejected outright (extra=forbid).
        status, body = await _submit(
            member_client, mtoken, project["id"], member_id="deadbeefdeadbeefdeadbeef"
        )
        assert status == 422, body

        listing = await member_client.get("/api/member/reports")
        assert listing.status_code == 200
        assert listing.json()["total"] == 0
    finally:
        await member_client.aclose()


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------
async def test_description_and_evidence_validation(
    client, make_admin, fetch_csrf, monkeypatch
):
    admin_token = await login_admin(client, make_admin, fetch_csrf)
    member_client, mtoken, project, _member, _readable = await _confirmed_member(
        client, admin_token, monkeypatch, email="validate@example.com", role="Backend Dev"
    )
    try:
        # Too long (> 500 chars).
        status, _ = await _submit(member_client, mtoken, project["id"], description="x" * 501)
        assert status == 422

        # Empty description.
        status, _ = await _submit(member_client, mtoken, project["id"], description="   ")
        assert status == 422

        # Non-http evidence link.
        status, _ = await _submit(
            member_client, mtoken, project["id"], evidence_links=["javascript:alert(1)"]
        )
        assert status == 422

        # Valid submit, exactly at the cap, with evidence + role snapshot.
        status, body = await _submit(
            member_client,
            mtoken,
            project["id"],
            description="y" * 500,
            evidence_links=["https://example.com/pr/1", "http://builds.example.com/2"],
        )
        assert status == 201, body
        assert body["status"] == "pending"
        assert body["role"] == "Backend Dev"
        assert body["version"] == 0
        assert body["editable"] is True
        assert body["evidence_links"] == [
            "https://example.com/pr/1",
            "http://builds.example.com/2",
        ]
    finally:
        await member_client.aclose()


async def test_duplicate_submit_is_idempotent(
    client, make_admin, fetch_csrf, monkeypatch
):
    admin_token = await login_admin(client, make_admin, fetch_csrf)
    member_client, mtoken, project, _member, _readable = await _confirmed_member(
        client, admin_token, monkeypatch, email="dup@example.com"
    )
    try:
        status, first = await _submit(
            member_client, mtoken, project["id"], client_request_id="req-123"
        )
        assert status == 201, first
        # A retry/double-click with the same idempotency key returns the same
        # report and never creates a second one.
        status, second = await _submit(
            member_client, mtoken, project["id"], client_request_id="req-123"
        )
        assert status == 201, second
        assert second["id"] == first["id"]

        listing = await member_client.get("/api/member/reports")
        assert listing.json()["total"] == 1

        # A different key creates a distinct report.
        status, third = await _submit(
            member_client, mtoken, project["id"], client_request_id="req-456"
        )
        assert third["id"] != first["id"]
        assert (await member_client.get("/api/member/reports")).json()["total"] == 2
    finally:
        await member_client.aclose()


# ---------------------------------------------------------------------------
# Ownership
# ---------------------------------------------------------------------------
async def test_member_cannot_see_another_members_report(
    client, make_admin, fetch_csrf, monkeypatch
):
    admin_token = await login_admin(client, make_admin, fetch_csrf)
    a_client, a_token, a_project, _am, _ar = await _confirmed_member(
        client, admin_token, monkeypatch, email="owner-a@example.com"
    )
    b_client, b_token, _b_project, _bm, _br = await _confirmed_member(
        client, admin_token, monkeypatch, email="owner-b@example.com", title="Other Project"
    )
    try:
        _status, report = await _submit(a_client, a_token, a_project["id"])
        # B can't read A's report.
        res = await b_client.get(f"/api/member/reports/{report['id']}")
        assert res.status_code == 404, res.text
        # B can't edit A's report either.
        res = await b_client.patch(
            f"/api/member/reports/{report['id']}",
            json={"description": "hijack"},
            headers={"X-CSRF-Token": b_token},
        )
        assert res.status_code == 404, res.text
    finally:
        await a_client.aclose()
        await b_client.aclose()


# ---------------------------------------------------------------------------
# Edit / resubmit + preserved review history
# ---------------------------------------------------------------------------
async def test_edit_resubmit_preserves_review_history(
    client, make_admin, fetch_csrf, monkeypatch
):
    admin_token = await login_admin(client, make_admin, fetch_csrf)
    member_client, mtoken, project, _member, _readable = await _confirmed_member(
        client, admin_token, monkeypatch, email="revise@example.com"
    )
    try:
        _s, report = await _submit(member_client, mtoken, project["id"], description="v1")

        # Admin requests changes (with required feedback).
        res = await client.post(
            f"/api/admin/reports/{report['id']}/decision",
            json={"action": "request_changes", "feedback": "Add evidence please"},
            headers={"X-CSRF-Token": admin_token},
        )
        assert res.status_code == 200, res.text
        assert res.json()["status"] == "changes_requested"

        # Member edits + resubmits: status returns to pending, version bumps,
        # and the earlier decision is retained in history.
        res = await member_client.patch(
            f"/api/member/reports/{report['id']}",
            json={"description": "v2 with evidence", "evidence_links": ["https://x.example.com"]},
            headers={"X-CSRF-Token": mtoken},
        )
        assert res.status_code == 200, res.text
        revised = res.json()
        assert revised["status"] == "pending"
        assert revised["version"] == 1
        assert len(revised["review_history"]) == 1
        assert revised["review_history"][0]["status"] == "changes_requested"
        assert revised["review_history"][0]["feedback"] == "Add evidence please"

        # Approve → second history entry appended (nothing overwritten).
        res = await client.post(
            f"/api/admin/reports/{report['id']}/decision",
            json={"action": "approve"},
            headers={"X-CSRF-Token": admin_token},
        )
        assert res.status_code == 200, res.text
        approved = res.json()
        assert approved["status"] == "approved"
        assert len(approved["review_history"]) == 2
        assert approved["review_history"][1]["status"] == "approved"
        assert approved["review_history"][1]["version"] == 1

        # An approved report is finalised.
        res = await member_client.patch(
            f"/api/member/reports/{report['id']}",
            json={"description": "too late"},
            headers={"X-CSRF-Token": mtoken},
        )
        assert res.status_code == 409, res.text
    finally:
        await member_client.aclose()


# ---------------------------------------------------------------------------
# Admin review RBAC / CSRF / states
# ---------------------------------------------------------------------------
async def test_admin_decision_requires_admin_role_and_csrf(
    client, make_admin, fetch_csrf, monkeypatch
):
    admin_token = await login_admin(client, make_admin, fetch_csrf)
    member_client, mtoken, project, _member, _readable = await _confirmed_member(
        client, admin_token, monkeypatch, email="rbac@example.com"
    )
    try:
        _s, report = await _submit(member_client, mtoken, project["id"])

        # No CSRF header → 403.
        res = await client.post(
            f"/api/admin/reports/{report['id']}/decision", json={"action": "approve"}
        )
        assert res.status_code == 403, res.text

        # Editor role cannot decide.
        editor_token = await login_admin(
            client, make_admin, fetch_csrf, email="editor@example.com", role=Role.EDITOR
        )
        res = await client.post(
            f"/api/admin/reports/{report['id']}/decision",
            json={"action": "approve"},
            headers={"X-CSRF-Token": editor_token},
        )
        assert res.status_code == 403, res.text

        # A member session cannot reach the admin surface.
        res = await member_client.post(
            f"/api/admin/reports/{report['id']}/decision",
            json={"action": "approve"},
            headers={"X-CSRF-Token": mtoken},
        )
        assert res.status_code in (401, 403), res.text
    finally:
        await member_client.aclose()


async def test_request_changes_requires_feedback_and_pending(
    client, make_admin, fetch_csrf, monkeypatch
):
    admin_token = await login_admin(client, make_admin, fetch_csrf)
    member_client, mtoken, project, _member, _readable = await _confirmed_member(
        client, admin_token, monkeypatch, email="states@example.com"
    )
    try:
        _s, report = await _submit(member_client, mtoken, project["id"])

        res = await client.post(
            f"/api/admin/reports/{report['id']}/decision",
            json={"action": "request_changes"},
            headers={"X-CSRF-Token": admin_token},
        )
        assert res.status_code == 422, res.text

        res = await client.post(
            f"/api/admin/reports/{report['id']}/decision",
            json={"action": "approve"},
            headers={"X-CSRF-Token": admin_token},
        )
        assert res.status_code == 200, res.text

        # Can't decide twice.
        res = await client.post(
            f"/api/admin/reports/{report['id']}/decision",
            json={"action": "request_changes", "feedback": "again"},
            headers={"X-CSRF-Token": admin_token},
        )
        assert res.status_code == 409, res.text
    finally:
        await member_client.aclose()


# ---------------------------------------------------------------------------
# Admin queue: filters + search
# ---------------------------------------------------------------------------
async def test_admin_queue_filters_and_search(
    client, make_admin, fetch_csrf, monkeypatch
):
    admin_token = await login_admin(client, make_admin, fetch_csrf)
    a_client, a_token, a_project, _am, _ar = await _confirmed_member(
        client, admin_token, monkeypatch, email="alice@example.com", title="Alpha Project"
    )
    b_client, b_token, b_project, _bm, _br = await _confirmed_member(
        client, admin_token, monkeypatch, email="bob@example.com", title="Beta Project"
    )
    try:
        _s, ra = await _submit(a_client, a_token, a_project["id"], description="alpha work")
        _s, rb = await _submit(b_client, b_token, b_project["id"], description="beta work")
        # Approve only B.
        await client.post(
            f"/api/admin/reports/{rb['id']}/decision",
            json={"action": "approve"},
            headers={"X-CSRF-Token": admin_token},
        )

        # Status filter.
        pending = await client.get("/api/admin/reports", params={"status": "pending"})
        assert pending.status_code == 200
        assert pending.json()["total"] == 1
        assert pending.json()["items"][0]["id"] == ra["id"]

        approved = await client.get("/api/admin/reports", params={"status": "approved"})
        assert approved.json()["total"] == 1

        # Filter by project.
        by_project = await client.get(
            "/api/admin/reports", params={"activity_id": a_project["id"]}
        )
        assert by_project.json()["total"] == 1
        item = by_project.json()["items"][0]
        assert item["member_name"] == "alice"
        assert item["member_readable_id"] == _ar

        # Search by member name.
        by_name = await client.get("/api/admin/reports", params={"search": "alice"})
        assert by_name.json()["total"] == 1

        # Search by project title.
        by_title = await client.get("/api/admin/reports", params={"search": "beta project"})
        assert by_title.json()["total"] == 1

        # No matches.
        none = await client.get("/api/admin/reports", params={"search": "zzzzz"})
        assert none.json()["total"] == 0
    finally:
        await a_client.aclose()
        await b_client.aclose()


# ---------------------------------------------------------------------------
# Member projects overview + contribution history
# ---------------------------------------------------------------------------
async def test_my_projects_and_contribution_history(
    client, make_admin, fetch_csrf, monkeypatch
):
    admin_token = await login_admin(client, make_admin, fetch_csrf)
    member_client, mtoken, project, member, readable = await _confirmed_member(
        client, admin_token, monkeypatch, email="contributor@example.com", role="QA"
    )
    try:
        # An invited-but-not-confirmed project must never appear.
        other = await create_activity(
            client, admin_token, title="Invite Only", activity_type="project"
        )
        await publish_activity(client, admin_token, other["id"])
        await invite_to_activity(
            client, admin_token, other["id"], [{"member_id": member["id"]}]
        )

        _s, approved = await _submit(member_client, mtoken, project["id"], description="done 1")
        _s, pending = await _submit(member_client, mtoken, project["id"], description="wip")
        await client.post(
            f"/api/admin/reports/{approved['id']}/decision",
            json={"action": "approve"},
            headers={"X-CSRF-Token": admin_token},
        )

        projects = await member_client.get("/api/member/reports/projects")
        assert projects.status_code == 200, projects.text
        slugs = [p["slug"] for p in projects.json()["items"]]
        assert project["slug"] in slugs
        assert other["slug"] not in slugs
        row = next(p for p in projects.json()["items"] if p["slug"] == project["slug"])
        assert row["role"] == "QA"
        assert row["report_count"] == 2
        assert row["approved_count"] == 1
        assert row["pending_count"] == 1

        history = await member_client.get("/api/member/reports/contributions")
        assert history.status_code == 200, history.text
        data = history.json()
        assert data["total_reports"] == 1
        assert len(data["items"]) == 1
        group = data["items"][0]
        assert group["activity_id"] == project["id"]
        assert group["role"] == "QA"
        assert group["report_count"] == 1
        assert group["reports"][0]["description"] == "done 1"
        # The pending report is excluded from official contributions.
        assert all(
            r["description"] != "wip" for r in group["reports"]
        )
    finally:
        await member_client.aclose()


async def test_member_list_filter_by_activity(
    client, make_admin, fetch_csrf, monkeypatch
):
    admin_token = await login_admin(client, make_admin, fetch_csrf)
    member_client, mtoken, project, _member, _readable = await _confirmed_member(
        client, admin_token, monkeypatch, email="filter@example.com"
    )
    try:
        _s, r = await _submit(member_client, mtoken, project["id"])
        listed = await member_client.get(
            "/api/member/reports", params={"activity_id": project["id"]}
        )
        assert listed.json()["total"] == 1
        other = await member_client.get(
            "/api/member/reports", params={"activity_id": "000000000000000000000000"}
        )
        assert other.json()["total"] == 0
    finally:
        await member_client.aclose()
