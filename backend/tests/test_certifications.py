"""Certification review tests.

Covers eligibility, the frozen snapshot, the active-request uniqueness rule,
reviewer decisions (RBAC + required feedback), resubmission, changed-since-review
derivation, and delete-blocking while a review is active.
"""

from __future__ import annotations

from httpx import ASGITransport, AsyncClient

from app.main import app
from app.models.admin import Role
from tests._content_helpers import (
    apply_certification,
    capture_onboarding_token,
    create_work,
    login_admin,
    onboard_member,
    patch_work,
    publish_work,
)


def _second_client() -> AsyncClient:
    return AsyncClient(transport=ASGITransport(app=app), base_url="https://testserver")


async def _login_admin_on(admin_client, make_admin, *, email: str, role=Role.OWNER) -> str:
    await make_admin(email, role=role)
    csrf = await admin_client.get("/api/auth/csrf")
    assert csrf.status_code == 200, csrf.text
    login = await admin_client.post(
        "/api/auth/login",
        json={"email": email, "password": "CorrectHorse!Battery9"},
        headers={"X-CSRF-Token": csrf.json()["csrfToken"]},
    )
    assert login.status_code == 200, login.text
    csrf = await admin_client.get("/api/auth/csrf")
    return csrf.json()["csrfToken"]


async def _member_with_work(admin_client, make_admin, fetch_csrf, monkeypatch, *, email):
    admin_token = await login_admin(admin_client, make_admin, fetch_csrf)
    member_client = _second_client()
    capture = capture_onboarding_token(monkeypatch)
    _readable, member_token = await onboard_member(
        member_client, admin_client, admin_token, capture, email=email
    )
    return member_client, member_token, admin_token


async def test_apply_requires_published(client, make_admin, fetch_csrf, monkeypatch):
    member_client, token, _ = await _member_with_work(
        client, make_admin, fetch_csrf, monkeypatch, email="c1@example.com"
    )
    work = await create_work(member_client, token, title="Draft work")
    status, body = await apply_certification(member_client, token, work["id"])
    assert status == 409
    assert body["error"]["code"] == "WORK_NOT_PUBLISHED"


async def test_apply_requires_ownership(client, make_admin, fetch_csrf, monkeypatch):
    member_client, token, admin_token = await _member_with_work(
        client, make_admin, fetch_csrf, monkeypatch, email="c2@example.com"
    )
    work = await create_work(member_client, token, title="Owned")
    await publish_work(member_client, token, work["id"])

    other_client = _second_client()
    capture = capture_onboarding_token(monkeypatch)
    _r, other_token = await onboard_member(
        other_client, client, admin_token, capture, email="c2-other@example.com"
    )
    status, body = await apply_certification(other_client, other_token, work["id"])
    assert status == 404
    assert body["error"]["code"] == "WORK_NOT_FOUND"


async def test_apply_creates_frozen_snapshot(client, make_admin, fetch_csrf, monkeypatch):
    member_client, token, _ = await _member_with_work(
        client, make_admin, fetch_csrf, monkeypatch, email="c3@example.com"
    )
    work = await create_work(member_client, token, title="Snapshot Me", summary="Original summary")
    await publish_work(member_client, token, work["id"])

    status, body = await apply_certification(member_client, token, work["id"])
    assert status == 201, body
    request_id = body["id"]
    assert body["status"] == "submitted"
    assert body["active"] is True
    assert body["snapshot"]["summary"] == "Original summary"
    assert body["snapshot_version"] == 1  # publish bumped the version

    # Editing the work must NOT change the frozen snapshot.
    await patch_work(member_client, token, work["id"], summary="Changed later")
    detail = await member_client.get(f"/api/member/certifications/{request_id}")
    assert detail.status_code == 200
    assert detail.json()["snapshot"]["summary"] == "Original summary"


async def test_duplicate_apply_conflicts(client, make_admin, fetch_csrf, monkeypatch):
    member_client, token, _ = await _member_with_work(
        client, make_admin, fetch_csrf, monkeypatch, email="c4@example.com"
    )
    work = await create_work(member_client, token, title="Once")
    await publish_work(member_client, token, work["id"])
    status, _ = await apply_certification(member_client, token, work["id"])
    assert status == 201

    status, body = await apply_certification(member_client, token, work["id"])
    assert status == 409
    assert body["error"]["code"] == "CERTIFICATION_ALREADY_ACTIVE"


async def test_apply_requires_csrf(client, make_admin, fetch_csrf, monkeypatch):
    member_client, token, _ = await _member_with_work(
        client, make_admin, fetch_csrf, monkeypatch, email="c5@example.com"
    )
    work = await create_work(member_client, token, title="No CSRF")
    await publish_work(member_client, token, work["id"])
    res = await member_client.post(
        "/api/member/certifications", json={"work_id": work["id"]}
    )
    assert res.status_code == 403


async def test_editor_cannot_decide(client, make_admin, fetch_csrf, monkeypatch):
    member_client, token, _ = await _member_with_work(
        client, make_admin, fetch_csrf, monkeypatch, email="c6@example.com"
    )
    work = await create_work(member_client, token, title="RBAC")
    await publish_work(member_client, token, work["id"])
    _s, body = await apply_certification(member_client, token, work["id"])
    request_id = body["id"]

    editor_client = _second_client()
    editor_token = await _login_admin_on(
        editor_client, make_admin, email="editor@example.com", role=Role.EDITOR
    )
    res = await editor_client.post(
        f"/api/admin/certifications/{request_id}/decision",
        json={"action": "under_review"},
        headers={"X-CSRF-Token": editor_token},
    )
    assert res.status_code == 403


async def test_admin_can_approve(client, make_admin, fetch_csrf, monkeypatch):
    member_client, token, admin_token = await _member_with_work(
        client, make_admin, fetch_csrf, monkeypatch, email="c7@example.com"
    )
    work = await create_work(member_client, token, title="Approve Me")
    await publish_work(member_client, token, work["id"])
    _s, body = await apply_certification(member_client, token, work["id"])
    request_id = body["id"]

    review = await client.post(
        f"/api/admin/certifications/{request_id}/decision",
        json={"action": "under_review"},
        headers={"X-CSRF-Token": admin_token},
    )
    assert review.status_code == 200, review.text
    assert review.json()["status"] == "under_review"

    approve = await client.post(
        f"/api/admin/certifications/{request_id}/decision",
        json={"action": "approve"},
        headers={"X-CSRF-Token": admin_token},
    )
    assert approve.status_code == 200, approve.text
    assert approve.json()["status"] == "approved"
    assert approve.json()["active"] is False

    # A terminal request frees the slot: a fresh application is allowed.
    status, _ = await apply_certification(member_client, token, work["id"])
    assert status == 201


async def test_request_changes_requires_feedback_and_resubmit(
    client, make_admin, fetch_csrf, monkeypatch
):
    member_client, token, admin_token = await _member_with_work(
        client, make_admin, fetch_csrf, monkeypatch, email="c8@example.com"
    )
    work = await create_work(member_client, token, title="Needs Work")
    await publish_work(member_client, token, work["id"])
    _s, body = await apply_certification(member_client, token, work["id"])
    request_id = body["id"]

    missing = await client.post(
        f"/api/admin/certifications/{request_id}/decision",
        json={"action": "request_changes"},
        headers={"X-CSRF-Token": admin_token},
    )
    assert missing.status_code == 422
    assert missing.json()["error"]["code"] == "FEEDBACK_REQUIRED"

    changed = await client.post(
        f"/api/admin/certifications/{request_id}/decision",
        json={"action": "request_changes", "feedback": "Please add detail"},
        headers={"X-CSRF-Token": admin_token},
    )
    assert changed.status_code == 200, changed.text
    assert changed.json()["status"] == "changes_requested"
    assert changed.json()["active"] is True

    # Resubmission reuses the SAME request with a fresh snapshot version.
    await patch_work(member_client, token, work["id"], summary="Improved")
    status, resubmitted = await apply_certification(member_client, token, work["id"])
    assert status == 201
    assert resubmitted["id"] == request_id
    assert resubmitted["status"] == "submitted"
    assert resubmitted["snapshot"]["summary"] == "Improved"


async def test_reject_requires_feedback(client, make_admin, fetch_csrf, monkeypatch):
    member_client, token, admin_token = await _member_with_work(
        client, make_admin, fetch_csrf, monkeypatch, email="c9@example.com"
    )
    work = await create_work(member_client, token, title="Reject Me")
    await publish_work(member_client, token, work["id"])
    _s, body = await apply_certification(member_client, token, work["id"])

    res = await client.post(
        f"/api/admin/certifications/{body['id']}/decision",
        json={"action": "reject"},
        headers={"X-CSRF-Token": admin_token},
    )
    assert res.status_code == 422


async def test_changed_since_review_flag(client, make_admin, fetch_csrf, monkeypatch):
    member_client, token, admin_token = await _member_with_work(
        client, make_admin, fetch_csrf, monkeypatch, email="c10@example.com"
    )
    work = await create_work(member_client, token, title="Changed")
    await publish_work(member_client, token, work["id"])
    _s, body = await apply_certification(member_client, token, work["id"])
    request_id = body["id"]

    await client.post(
        f"/api/admin/certifications/{request_id}/decision",
        json={"action": "approve"},
        headers={"X-CSRF-Token": admin_token},
    )
    approved = await client.get(f"/api/admin/certifications/{request_id}")
    assert approved.json()["changed_since_review"] is False

    await patch_work(member_client, token, work["id"], summary="Edited after approval")
    after = await client.get(f"/api/admin/certifications/{request_id}")
    assert after.json()["status"] == "approved"
    assert after.json()["changed_since_review"] is True


async def test_delete_blocked_while_review_active(client, make_admin, fetch_csrf, monkeypatch):
    member_client, token, admin_token = await _member_with_work(
        client, make_admin, fetch_csrf, monkeypatch, email="c11@example.com"
    )
    work = await create_work(member_client, token, title="No Delete")
    await publish_work(member_client, token, work["id"])
    _s, body = await apply_certification(member_client, token, work["id"])
    request_id = body["id"]

    res = await member_client.delete(
        f"/api/member/works/{work['id']}", headers={"X-CSRF-Token": token}
    )
    assert res.status_code == 409
    assert res.json()["error"]["code"] == "CERTIFICATION_IN_PROGRESS"

    await client.post(
        f"/api/admin/certifications/{request_id}/decision",
        json={"action": "approve"},
        headers={"X-CSRF-Token": admin_token},
    )
    res = await member_client.delete(
        f"/api/member/works/{work['id']}", headers={"X-CSRF-Token": token}
    )
    assert res.status_code == 200


async def test_request_isolation_between_members(client, make_admin, fetch_csrf, monkeypatch):
    member_client, token, admin_token = await _member_with_work(
        client, make_admin, fetch_csrf, monkeypatch, email="c12@example.com"
    )
    work = await create_work(member_client, token, title="Io")
    await publish_work(member_client, token, work["id"])
    _s, body = await apply_certification(member_client, token, work["id"])

    other_client = _second_client()
    capture = capture_onboarding_token(monkeypatch)
    _r, other_token = await onboard_member(
        other_client, client, admin_token, capture, email="c12-other@example.com"
    )
    res = await other_client.get(f"/api/member/certifications/{body['id']}")
    assert res.status_code == 404


async def test_admin_list_filters_by_status(client, make_admin, fetch_csrf, monkeypatch):
    member_client, token, _ = await _member_with_work(
        client, make_admin, fetch_csrf, monkeypatch, email="c13@example.com"
    )
    work = await create_work(member_client, token, title="Filter Me")
    await publish_work(member_client, token, work["id"])
    await apply_certification(member_client, token, work["id"])

    listing = await client.get("/api/admin/certifications?status=submitted")
    assert listing.status_code == 200
    assert listing.json()["total"] == 1
    empty = await client.get("/api/admin/certifications?status=approved")
    assert empty.json()["total"] == 0


async def _work_ref(client, work_id: str) -> dict:
    res = await client.get(f"/api/member/works/{work_id}")
    assert res.status_code == 200, res.text
    return res.json()["certification"]


async def test_work_certification_ref_eligibility_lifecycle(
    client, make_admin, fetch_csrf, monkeypatch
):
    """The per-work `certification` ref must agree with the request state at
    every step: a published work with no request is eligible (`reviewable`)."""
    member_client, token, admin_token = await _member_with_work(
        client, make_admin, fetch_csrf, monkeypatch, email="c14@example.com"
    )
    work = await create_work(member_client, token, title="Lifecycle")
    work_id = work["id"]

    # Draft: not eligible, no status.
    draft = await _work_ref(member_client, work_id)
    assert draft["reviewable"] is False
    assert draft["status"] is None

    # Published with no request: eligible (the regression this guards).
    published = await publish_work(member_client, token, work_id)
    assert published["certification"]["reviewable"] is True
    assert published["certification"]["status"] is None
    fetched = await _work_ref(member_client, work_id)
    assert fetched["reviewable"] is True
    assert fetched["status"] is None

    # Active request: not eligible; current status surfaced.
    _, applied = await apply_certification(member_client, token, work_id)
    submitted = await _work_ref(member_client, work_id)
    assert submitted["reviewable"] is False
    assert submitted["status"] == "submitted"
    assert submitted["request_id"] == applied["id"]

    await client.post(
        f"/api/admin/certifications/{applied['id']}/decision",
        json={"action": "under_review"},
        headers={"X-CSRF-Token": admin_token},
    )
    under = await _work_ref(member_client, work_id)
    assert under["reviewable"] is False
    assert under["status"] == "under_review"

    # changes_requested: resubmission permitted.
    await client.post(
        f"/api/admin/certifications/{applied['id']}/decision",
        json={"action": "request_changes", "feedback": "Please add detail"},
        headers={"X-CSRF-Token": admin_token},
    )
    changed = await _work_ref(member_client, work_id)
    assert changed["reviewable"] is True
    assert changed["status"] == "changes_requested"

    # rejected: a new review is permitted.
    await client.post(
        f"/api/admin/certifications/{applied['id']}/decision",
        json={"action": "reject", "feedback": "Not ready"},
        headers={"X-CSRF-Token": admin_token},
    )
    rejected = await _work_ref(member_client, work_id)
    assert rejected["reviewable"] is True
    assert rejected["status"] == "rejected"

    # The list endpoint must agree with the single-work endpoint.
    listed = await member_client.get("/api/member/works")
    assert listed.status_code == 200
    card = next(item for item in listed.json()["items"] if item["id"] == work_id)
    assert card["certification"]["reviewable"] is True
    assert card["certification"]["status"] == "rejected"


async def test_work_certification_ref_after_approval(
    client, make_admin, fetch_csrf, monkeypatch
):
    member_client, token, admin_token = await _member_with_work(
        client, make_admin, fetch_csrf, monkeypatch, email="c15@example.com"
    )
    work = await create_work(member_client, token, title="Approved Ref")
    await publish_work(member_client, token, work["id"])
    _, applied = await apply_certification(member_client, token, work["id"])

    await client.post(
        f"/api/admin/certifications/{applied['id']}/decision",
        json={"action": "approve"},
        headers={"X-CSRF-Token": admin_token},
    )

    approved = await _work_ref(member_client, work["id"])
    assert approved["status"] == "approved"
    assert approved["reviewable"] is True
    assert approved["changed_since_review"] is False


async def test_draft_work_certification_list_ref_is_not_reviewable(
    client, make_admin, fetch_csrf, monkeypatch
):
    member_client, token, _ = await _member_with_work(
        client, make_admin, fetch_csrf, monkeypatch, email="c16@example.com"
    )
    await create_work(member_client, token, title="Still Draft")

    listed = await member_client.get("/api/member/works")
    card = listed.json()["items"][0]
    assert card["certification"]["reviewable"] is False
    assert card["certification"]["status"] is None
