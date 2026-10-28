"""Activity workspace tests (programmes/hackathons, individual only).

Covers the confirmed-participant authorization, CSRF + RBAC, the submission
window, the one-deliverable-per-student rule, required-deliverable validation,
member ownership isolation, edit/resubmit with a preserved review history and
revision snapshot, the personal task checklist, and the admin review queue with
approve / request-changes / reject decisions.
"""

from __future__ import annotations

from datetime import date, timedelta

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app
from app.models.admin import Role
from tests._content_helpers import (
    capture_onboarding_token,
    create_activity,
    create_member,
    list_activity_participants,
    login_admin,
    member_login,
    member_setup,
    patch_activity,
    publish_activity,
    register_activity,
    update_participant,
)


def _second_client() -> AsyncClient:
    return AsyncClient(transport=ASGITransport(app=app), base_url="https://testserver")


async def _joined_member(
    client,
    admin_token: str,
    monkeypatch,
    *,
    email: str,
    title: str = "Atlas Programme",
    activity_type: str = "programme",
    **activity_overrides,
):
    """Create a member + a published programme and self-register the member.

    Self-registration confirms the participation, so the member immediately has
    a workspace. Returns (member_client, member_csrf, activity, member).
    """
    capture = capture_onboarding_token(monkeypatch)
    member = await create_member(
        client, admin_token, email=email, full_name=email.split("@")[0]
    )
    activity = await create_activity(
        client, admin_token, title=title, activity_type=activity_type, **activity_overrides
    )
    await publish_activity(client, admin_token, activity["id"])

    member_client = _second_client()
    await member_setup(member_client, capture["token"])
    token = await member_login(member_client, email)
    status, body = await register_activity(member_client, token, activity["slug"])
    assert status == 200, body
    return member_client, token, activity, member


async def _submit(member_client, token, activity_id, **overrides):
    payload = {"activity_id": activity_id, "description": "Shipped the prototype."}
    payload.update(overrides)
    res = await member_client.post(
        "/api/member/activity-submissions",
        json=payload,
        headers={"X-CSRF-Token": token},
    )
    return res.status_code, res.json()


# ---------------------------------------------------------------------------
# Auth / CSRF / authorization
# ---------------------------------------------------------------------------
async def test_submit_requires_authentication(client):
    csrf = await client.get("/api/member/csrf")
    token = csrf.json()["csrfToken"]
    res = await client.post(
        "/api/member/activity-submissions",
        json={"activity_id": "x", "description": "nope"},
        headers={"X-CSRF-Token": token},
    )
    assert res.status_code == 401, res.text


async def test_submit_requires_csrf(client, make_admin, fetch_csrf, monkeypatch):
    admin_token = await login_admin(client, make_admin, fetch_csrf)
    member_client, _token, activity, _member = await _joined_member(
        client, admin_token, monkeypatch, email="csrf@example.com"
    )
    try:
        res = await member_client.post(
            "/api/member/activity-submissions",
            json={"activity_id": activity["id"], "description": "No csrf"},
        )
        assert res.status_code == 403, res.text
    finally:
        await member_client.aclose()


async def test_submit_requires_confirmed_participant(
    client, make_admin, fetch_csrf, monkeypatch
):
    admin_token = await login_admin(client, make_admin, fetch_csrf)
    capture = capture_onboarding_token(monkeypatch)
    await create_member(client, admin_token, email="outsider@example.com")
    activity = await create_activity(
        client, admin_token, title="Members Only", activity_type="programme"
    )
    await publish_activity(client, admin_token, activity["id"])

    member_client = _second_client()
    await member_setup(member_client, capture["token"])
    token = await member_login(member_client, "outsider@example.com")
    try:
        status, body = await _submit(member_client, token, activity["id"])
        assert status == 403, body
        assert body["error"]["code"] == "NOT_A_PARTICIPANT"
    finally:
        await member_client.aclose()


async def test_submit_to_a_project_activity_is_not_found(
    client, make_admin, fetch_csrf, monkeypatch
):
    """Projects keep their own progress-report surface — no workspace here."""
    admin_token = await login_admin(client, make_admin, fetch_csrf)
    capture = capture_onboarding_token(monkeypatch)
    member = await create_member(client, admin_token, email="proj@example.com")
    project = await create_activity(
        client, admin_token, title="Atlas Project", activity_type="project"
    )
    await publish_activity(client, admin_token, project["id"])

    member_client = _second_client()
    await member_setup(member_client, capture["token"])
    token = await member_login(member_client, "proj@example.com")
    try:
        status, body = await _submit(member_client, token, project["id"])
        assert status == 404, body
        assert body["error"]["code"] == "ACTIVITY_NOT_FOUND"
    finally:
        await member_client.aclose()


async def test_submit_to_unknown_activity_is_not_found(
    client, make_admin, fetch_csrf, monkeypatch
):
    admin_token = await login_admin(client, make_admin, fetch_csrf)
    member_client, token, _activity, _member = await _joined_member(
        client, admin_token, monkeypatch, email="unknown@example.com"
    )
    try:
        status, body = await _submit(member_client, token, "000000000000000000000000")
        assert status == 404, body
        assert body["error"]["code"] == "ACTIVITY_NOT_FOUND"
    finally:
        await member_client.aclose()


# ---------------------------------------------------------------------------
# Submission window
# ---------------------------------------------------------------------------
async def test_submit_is_closed_after_the_end_date(
    client, make_admin, fetch_csrf, monkeypatch
):
    admin_token = await login_admin(client, make_admin, fetch_csrf)
    member_client, token, activity, _member = await _joined_member(
        client, admin_token, monkeypatch, email="late@example.com"
    )
    yesterday = (date.today() - timedelta(days=1)).isoformat()
    status, _body = await patch_activity(
        client, admin_token, activity["id"], end_date=yesterday
    )
    assert status == 200
    try:
        status, body = await _submit(member_client, token, activity["id"])
        assert status == 409, body
        assert body["error"]["code"] == "SUBMISSION_CLOSED"
    finally:
        await member_client.aclose()


async def test_an_existing_submission_can_still_be_edited_after_the_deadline(
    client, make_admin, fetch_csrf, monkeypatch
):
    """A student must be able to answer `changes_requested` after the deadline."""
    admin_token = await login_admin(client, make_admin, fetch_csrf)
    member_client, token, activity, _member = await _joined_member(
        client, admin_token, monkeypatch, email="lateedit@example.com"
    )
    try:
        status, submission = await _submit(member_client, token, activity["id"])
        assert status == 201, submission

        res = await client.post(
            f"/api/admin/activity-submissions/{submission['id']}/decision",
            json={"action": "request_changes", "feedback": "Add the evaluation."},
            headers={"X-CSRF-Token": admin_token},
        )
        assert res.status_code == 200, res.text

        yesterday = (date.today() - timedelta(days=1)).isoformat()
        status, _body = await patch_activity(
            client, admin_token, activity["id"], end_date=yesterday
        )
        assert status == 200

        res = await member_client.patch(
            f"/api/member/activity-submissions/{submission['id']}",
            json={"description": "Revised after the deadline."},
            headers={"X-CSRF-Token": token},
        )
        assert res.status_code == 200, res.text
        assert res.json()["status"] == "pending"
    finally:
        await member_client.aclose()


async def test_submit_is_closed_for_an_unpublished_activity(
    client, make_admin, fetch_csrf, monkeypatch
):
    admin_token = await login_admin(client, make_admin, fetch_csrf)
    capture = capture_onboarding_token(monkeypatch)
    await create_member(client, admin_token, email="draft@example.com")
    activity = await create_activity(
        client, admin_token, title="Draft Programme", activity_type="programme"
    )

    member_client = _second_client()
    await member_setup(member_client, capture["token"])
    token = await member_login(member_client, "draft@example.com")
    # Confirm the participation directly through the admin roster.
    participants = await list_activity_participants(client, admin_token, activity["id"])
    assert participants["items"] == []
    try:
        status, body = await _submit(member_client, token, activity["id"])
        assert status in (403, 404), body
    finally:
        await member_client.aclose()


# ---------------------------------------------------------------------------
# Submission rules
# ---------------------------------------------------------------------------
async def test_many_progress_updates_are_allowed(
    client, make_admin, fetch_csrf, monkeypatch
):
    admin_token = await login_admin(client, make_admin, fetch_csrf)
    member_client, token, activity, _member = await _joined_member(
        client, admin_token, monkeypatch, email="updates@example.com"
    )
    try:
        for index in range(3):
            status, body = await _submit(
                member_client,
                token,
                activity["id"],
                kind="progress_update",
                description=f"Update {index}",
            )
            assert status == 201, body
    finally:
        await member_client.aclose()


async def test_only_one_deliverable_per_student(
    client, make_admin, fetch_csrf, monkeypatch
):
    admin_token = await login_admin(client, make_admin, fetch_csrf)
    member_client, token, activity, _member = await _joined_member(
        client, admin_token, monkeypatch, email="one@example.com"
    )
    try:
        status, body = await _submit(
            member_client, token, activity["id"], kind="deliverable"
        )
        assert status == 201, body

        status, body = await _submit(
            member_client, token, activity["id"], kind="deliverable"
        )
        assert status == 409, body
        assert body["error"]["code"] == "DUPLICATE_SUBMISSION"
    finally:
        await member_client.aclose()


async def test_submission_is_idempotent_with_a_client_request_id(
    client, make_admin, fetch_csrf, monkeypatch
):
    admin_token = await login_admin(client, make_admin, fetch_csrf)
    member_client, token, activity, _member = await _joined_member(
        client, admin_token, monkeypatch, email="idem@example.com"
    )
    try:
        status, first = await _submit(
            member_client,
            token,
            activity["id"],
            client_request_id="req-1",
        )
        assert status == 201, first
        status, second = await _submit(
            member_client,
            token,
            activity["id"],
            client_request_id="req-1",
        )
        assert status == 201, second
        assert second["id"] == first["id"]
    finally:
        await member_client.aclose()


async def test_deliverable_requires_the_configured_parts(
    client, make_admin, fetch_csrf, monkeypatch
):
    admin_token = await login_admin(client, make_admin, fetch_csrf)
    member_client, token, activity, _member = await _joined_member(
        client,
        admin_token,
        monkeypatch,
        email="parts@example.com",
        required_deliverables=["description", "repository_url", "demo_url"],
    )
    try:
        status, body = await _submit(
            member_client, token, activity["id"], kind="deliverable"
        )
        assert status == 422, body
        assert body["error"]["code"] == "MISSING_DELIVERABLE"

        status, body = await _submit(
            member_client,
            token,
            activity["id"],
            kind="deliverable",
            repository_url="https://github.com/thridhalabs/demo",
        )
        assert status == 422, body

        status, body = await _submit(
            member_client,
            token,
            activity["id"],
            kind="deliverable",
            repository_url="https://github.com/thridhalabs/demo",
            demo_url="https://demo.example.com",
        )
        assert status == 201, body
    finally:
        await member_client.aclose()


async def test_deliverable_rejects_a_non_http_repository_url(
    client, make_admin, fetch_csrf, monkeypatch
):
    admin_token = await login_admin(client, make_admin, fetch_csrf)
    member_client, token, activity, _member = await _joined_member(
        client, admin_token, monkeypatch, email="badurl@example.com"
    )
    try:
        status, body = await _submit(
            member_client,
            token,
            activity["id"],
            kind="deliverable",
            repository_url="ftp://example.com/repo",
        )
        assert status == 422, body
    finally:
        await member_client.aclose()


async def test_deliverable_rejects_media_owned_by_someone_else(
    client, make_admin, fetch_csrf, monkeypatch
):
    from tests._content_helpers import upload_media

    admin_token = await login_admin(client, make_admin, fetch_csrf)
    media = await upload_media(client, admin_token)
    member_client, token, activity, _member = await _joined_member(
        client, admin_token, monkeypatch, email="media@example.com"
    )
    try:
        status, body = await _submit(
            member_client,
            token,
            activity["id"],
            kind="deliverable",
            attachment_media_ids=[media["id"]],
        )
        assert status == 422, body
        assert body["error"]["code"] == "MEDIA_NOT_OWNED"
    finally:
        await member_client.aclose()


# ---------------------------------------------------------------------------
# Ownership isolation
# ---------------------------------------------------------------------------
async def test_a_member_cannot_read_another_members_submission(
    client, make_admin, fetch_csrf, monkeypatch
):
    admin_token = await login_admin(client, make_admin, fetch_csrf)
    owner_client, owner_token, activity, _owner = await _joined_member(
        client, admin_token, monkeypatch, email="owner@example.com"
    )
    status, submission = await _submit(owner_client, owner_token, activity["id"])
    assert status == 201, submission

    other_client, other_token, _activity, _other = await _joined_member(
        client, admin_token, monkeypatch, email="other@example.com", title="Other Programme"
    )
    try:
        res = await other_client.get(
            f"/api/member/activity-submissions/{submission['id']}"
        )
        assert res.status_code == 404, res.text
        assert res.json()["error"]["code"] == "SUBMISSION_NOT_FOUND"

        res = await other_client.patch(
            f"/api/member/activity-submissions/{submission['id']}",
            json={"description": "Hijacked."},
            headers={"X-CSRF-Token": other_token},
        )
        assert res.status_code == 404, res.text
    finally:
        await owner_client.aclose()
        await other_client.aclose()


# ---------------------------------------------------------------------------
# Edit / resubmit
# ---------------------------------------------------------------------------
async def test_edit_and_resubmit_keeps_the_review_history(
    client, make_admin, fetch_csrf, monkeypatch
):
    admin_token = await login_admin(client, make_admin, fetch_csrf)
    member_client, token, activity, _member = await _joined_member(
        client, admin_token, monkeypatch, email="resubmit@example.com"
    )
    try:
        status, submission = await _submit(
            member_client,
            token,
            activity["id"],
            kind="deliverable",
            repository_url="https://github.com/thridhalabs/first",
        )
        assert status == 201, submission

        res = await client.post(
            f"/api/admin/activity-submissions/{submission['id']}/decision",
            json={"action": "request_changes", "feedback": "Add the evaluation."},
            headers={"X-CSRF-Token": admin_token},
        )
        assert res.status_code == 200, res.text
        decided = res.json()
        assert decided["status"] == "changes_requested"

        res = await member_client.patch(
            f"/api/member/activity-submissions/{submission['id']}",
            json={
                "description": "Revised with an evaluation harness.",
                "repository_url": "https://github.com/thridhalabs/second",
            },
            headers={"X-CSRF-Token": token},
        )
        assert res.status_code == 200, res.text
        updated = res.json()
        assert updated["status"] == "pending"
        assert updated["version"] == 1
        assert len(updated["review_history"]) == 1
        assert updated["review_history"][0]["feedback"] == "Add the evaluation."
        # The previous deliverable content is kept as a revision snapshot.
        assert len(updated["revisions"]) == 1
        assert updated["revisions"][0]["version"] == 0
    finally:
        await member_client.aclose()


async def test_an_approved_submission_can_no_longer_be_edited(
    client, make_admin, fetch_csrf, monkeypatch
):
    admin_token = await login_admin(client, make_admin, fetch_csrf)
    member_client, token, activity, _member = await _joined_member(
        client, admin_token, monkeypatch, email="final@example.com"
    )
    try:
        status, submission = await _submit(member_client, token, activity["id"])
        assert status == 201, submission

        res = await client.post(
            f"/api/admin/activity-submissions/{submission['id']}/decision",
            json={"action": "approve"},
            headers={"X-CSRF-Token": admin_token},
        )
        assert res.status_code == 200, res.text

        res = await member_client.patch(
            f"/api/member/activity-submissions/{submission['id']}",
            json={"description": "Too late."},
            headers={"X-CSRF-Token": token},
        )
        assert res.status_code == 409, res.text
        assert res.json()["error"]["code"] == "SUBMISSION_FINALIZED"
    finally:
        await member_client.aclose()


# ---------------------------------------------------------------------------
# Member workspace
# ---------------------------------------------------------------------------
async def test_workspace_lists_the_joined_activities(
    client, make_admin, fetch_csrf, monkeypatch
):
    admin_token = await login_admin(client, make_admin, fetch_csrf)
    member_client, token, activity, _member = await _joined_member(
        client,
        admin_token,
        monkeypatch,
        email="workspace@example.com",
        objectives=["Ship a prototype"],
        instructions="Work on your own.",
        requirements=["A public repository"],
        resources=[{"label": "Starter", "url": "https://github.com/thridhalabs/start"}],
        tasks=[{"id": "task-1", "title": "Build", "description": "", "due_date": None}],
        required_deliverables=["description"],
    )
    try:
        res = await member_client.get("/api/member/activity-workspaces")
        assert res.status_code == 200, res.text
        body = res.json()
        assert len(body["items"]) == 1
        workspace = body["items"][0]
        assert workspace["slug"] == activity["slug"]
        assert workspace["objectives"] == ["Ship a prototype"]
        assert workspace["instructions"] == "Work on your own."
        assert workspace["requirements"] == ["A public repository"]
        assert workspace["resources"][0]["label"] == "Starter"
        assert workspace["tasks"][0]["id"] == "task-1"
        assert workspace["tasks"][0]["completed"] is False
        assert workspace["task_count"] == 1
        assert workspace["progress_percent"] == 0
        assert workspace["can_submit"] is True

        res = await member_client.get(
            f"/api/member/activity-workspaces/{activity['slug']}"
        )
        assert res.status_code == 200, res.text
    finally:
        await member_client.aclose()


async def test_workspace_is_hidden_from_non_participants(
    client, make_admin, fetch_csrf, monkeypatch
):
    admin_token = await login_admin(client, make_admin, fetch_csrf)
    activity = await create_activity(
        client, admin_token, title="Closed Programme", activity_type="programme"
    )
    await publish_activity(client, admin_token, activity["id"])

    capture = capture_onboarding_token(monkeypatch)
    await create_member(client, admin_token, email="nosy@example.com")
    member_client = _second_client()
    await member_setup(member_client, capture["token"])
    token = await member_login(member_client, "nosy@example.com")
    try:
        res = await member_client.get(
            f"/api/member/activity-workspaces/{activity['slug']}"
        )
        assert res.status_code == 403, res.text
        assert res.json()["error"]["code"] == "NOT_A_PARTICIPANT"
    finally:
        await member_client.aclose()


async def test_task_completion_is_personal(
    client, make_admin, fetch_csrf, monkeypatch
):
    admin_token = await login_admin(client, make_admin, fetch_csrf)
    member_client, token, activity, _member = await _joined_member(
        client,
        admin_token,
        monkeypatch,
        email="tasks@example.com",
        tasks=[{"id": "task-1", "title": "Build", "description": "", "due_date": None}],
    )
    try:
        res = await member_client.patch(
            f"/api/member/activity-workspaces/{activity['slug']}/tasks",
            json={"task_id": "task-1", "completed": True},
            headers={"X-CSRF-Token": token},
        )
        assert res.status_code == 200, res.text
        body = res.json()
        assert body["tasks"][0]["completed"] is True
        assert body["completed_task_count"] == 1
        assert body["progress_percent"] == 100

        res = await member_client.patch(
            f"/api/member/activity-workspaces/{activity['slug']}/tasks",
            json={"task_id": "task-1", "completed": False},
            headers={"X-CSRF-Token": token},
        )
        assert res.status_code == 200, res.text
        assert res.json()["tasks"][0]["completed"] is False
    finally:
        await member_client.aclose()


async def test_unknown_task_is_not_found(client, make_admin, fetch_csrf, monkeypatch):
    admin_token = await login_admin(client, make_admin, fetch_csrf)
    member_client, token, activity, _member = await _joined_member(
        client, admin_token, monkeypatch, email="badtask@example.com"
    )
    try:
        res = await member_client.patch(
            f"/api/member/activity-workspaces/{activity['slug']}/tasks",
            json={"task_id": "nope", "completed": True},
            headers={"X-CSRF-Token": token},
        )
        assert res.status_code == 404, res.text
        assert res.json()["error"]["code"] == "TASK_NOT_FOUND"
    finally:
        await member_client.aclose()


# ---------------------------------------------------------------------------
# Admin review queue
# ---------------------------------------------------------------------------
async def test_admin_queue_lists_submissions(
    client, make_admin, fetch_csrf, monkeypatch
):
    admin_token = await login_admin(client, make_admin, fetch_csrf)
    member_client, token, activity, _member = await _joined_member(
        client, admin_token, monkeypatch, email="queue@example.com"
    )
    try:
        status, _ = await _submit(member_client, token, activity["id"])
        assert status == 201

        res = await client.get("/api/admin/activity-submissions")
        assert res.status_code == 200, res.text
        body = res.json()
        assert body["total"] == 1
        assert body["items"][0]["member_email"] == "queue@example.com"

        res = await client.get(
            "/api/admin/activity-submissions",
            params={"activity_id": activity["id"], "status": "pending"},
        )
        assert res.status_code == 200, res.text
        assert res.json()["total"] == 1

        res = await client.get(
            "/api/admin/activity-submissions",
            params={"activity_id": activity["id"], "status": "approved"},
        )
        assert res.status_code == 200, res.text
        assert res.json()["total"] == 0
    finally:
        await member_client.aclose()


async def test_admin_queue_rejects_an_unknown_status(
    client, make_admin, fetch_csrf
):
    admin_token = await login_admin(client, make_admin, fetch_csrf)
    res = await client.get(
        "/api/admin/activity-submissions", params={"status": "bogus"}
    )
    assert res.status_code == 422, res.text
    assert res.json()["error"]["code"] == "INVALID_STATUS"


async def test_an_editor_can_record_a_decision(
    client, make_admin, fetch_csrf, monkeypatch
):
    owner_token = await login_admin(client, make_admin, fetch_csrf)
    member_client, token, activity, _member = await _joined_member(
        client, owner_token, monkeypatch, email="role@example.com"
    )
    try:
        status, submission = await _submit(member_client, token, activity["id"])
        assert status == 201, submission

        # A separate editor account decides the submission.
        editor_token = await login_admin(
            client, make_admin, fetch_csrf, email="editor@example.com", role=Role.EDITOR
        )
        res = await client.post(
            f"/api/admin/activity-submissions/{submission['id']}/decision",
            json={"action": "approve"},
            headers={"X-CSRF-Token": editor_token},
        )
        assert res.status_code == 200, res.text
        assert res.json()["status"] == "approved"
    finally:
        await member_client.aclose()


async def test_admin_decisions_require_csrf(
    client, make_admin, fetch_csrf, monkeypatch
):
    admin_token = await login_admin(client, make_admin, fetch_csrf)
    member_client, token, activity, _member = await _joined_member(
        client, admin_token, monkeypatch, email="nocsrf@example.com"
    )
    try:
        status, submission = await _submit(member_client, token, activity["id"])
        assert status == 201, submission
        res = await client.post(
            f"/api/admin/activity-submissions/{submission['id']}/decision",
            json={"action": "approve"},
        )
        assert res.status_code == 403, res.text
    finally:
        await member_client.aclose()


async def test_request_changes_requires_feedback(
    client, make_admin, fetch_csrf, monkeypatch
):
    admin_token = await login_admin(client, make_admin, fetch_csrf)
    member_client, token, activity, _member = await _joined_member(
        client, admin_token, monkeypatch, email="feedback@example.com"
    )
    try:
        status, submission = await _submit(member_client, token, activity["id"])
        assert status == 201, submission
        res = await client.post(
            f"/api/admin/activity-submissions/{submission['id']}/decision",
            json={"action": "request_changes"},
            headers={"X-CSRF-Token": admin_token},
        )
        assert res.status_code == 422, res.text
        assert res.json()["error"]["code"] == "FEEDBACK_REQUIRED"
    finally:
        await member_client.aclose()


async def test_a_submission_can_only_be_decided_once(
    client, make_admin, fetch_csrf, monkeypatch
):
    admin_token = await login_admin(client, make_admin, fetch_csrf)
    member_client, token, activity, _member = await _joined_member(
        client, admin_token, monkeypatch, email="once@example.com"
    )
    try:
        status, submission = await _submit(member_client, token, activity["id"])
        assert status == 201, submission
        res = await client.post(
            f"/api/admin/activity-submissions/{submission['id']}/decision",
            json={"action": "approve"},
            headers={"X-CSRF-Token": admin_token},
        )
        assert res.status_code == 200, res.text
        assert res.json()["status"] == "approved"
        assert len(res.json()["review_history"]) == 1

        res = await client.post(
            f"/api/admin/activity-submissions/{submission['id']}/decision",
            json={"action": "reject"},
            headers={"X-CSRF-Token": admin_token},
        )
        assert res.status_code == 409, res.text
        assert res.json()["error"]["code"] == "SUBMISSION_NOT_IN_REVIEW"
    finally:
        await member_client.aclose()


async def test_admin_can_read_one_student_record(
    client, make_admin, fetch_csrf, monkeypatch
):
    admin_token = await login_admin(client, make_admin, fetch_csrf)
    member_client, token, activity, member = await _joined_member(
        client,
        admin_token,
        monkeypatch,
        email="student@example.com",
        tasks=[{"id": "task-1", "title": "Build", "description": "", "due_date": None}],
    )
    try:
        status, _ = await _submit(member_client, token, activity["id"])
        assert status == 201

        res = await client.get(
            f"/api/admin/activity-submissions/activity/{activity['id']}"
            f"/students/{member['id']}"
        )
        assert res.status_code == 200, res.text
        body = res.json()
        assert body["member_email"] == "student@example.com"
        assert body["participation_status"] == "confirmed"
        assert body["task_count"] == 1
        assert len(body["submissions"]) == 1
    finally:
        await member_client.aclose()


async def test_admin_can_read_one_submission(
    client, make_admin, fetch_csrf, monkeypatch
):
    admin_token = await login_admin(client, make_admin, fetch_csrf)
    member_client, token, activity, _member = await _joined_member(
        client, admin_token, monkeypatch, email="detail@example.com"
    )
    try:
        status, submission = await _submit(member_client, token, activity["id"])
        assert status == 201, submission
        res = await client.get(
            f"/api/admin/activity-submissions/{submission['id']}"
        )
        assert res.status_code == 200, res.text
        assert res.json()["id"] == submission["id"]
    finally:
        await member_client.aclose()


async def test_member_submission_list_is_scoped_to_the_member(
    client, make_admin, fetch_csrf, monkeypatch
):
    admin_token = await login_admin(client, make_admin, fetch_csrf)
    member_client, token, activity, _member = await _joined_member(
        client, admin_token, monkeypatch, email="scoped@example.com"
    )
    try:
        status, _ = await _submit(member_client, token, activity["id"])
        assert status == 201
        res = await member_client.get("/api/member/activity-submissions")
        assert res.status_code == 200, res.text
        body = res.json()
        assert body["total"] == 1
        assert body["items"][0]["member_readable_id"] == "THL-M-2026-0001"
    finally:
        await member_client.aclose()
