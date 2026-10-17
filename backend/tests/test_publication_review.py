"""Member Contributions to Official Projects — publication review + featuring.

Covers the member submit/withdraw flow, admin approve/request-changes/reject
decisions, RBAC (members can never decide; editors cannot decide/feature),
featuring rules (published + public only), and public eligibility/attribution
for featured contributions on the official Projects page.

The legacy direct publish/unpublish behaviour is unchanged and covered by
`test_works.py`; these tests exercise the *additive* review path.
"""

from __future__ import annotations

from httpx import ASGITransport, AsyncClient

from app.main import app
from app.models.admin import Role
from tests._content_helpers import (
    capture_onboarding_token,
    create_work,
    feature_work,
    login_admin,
    onboard_member,
    patch_work,
    publish_work,
    review_work,
    submit_work,
    withdraw_work,
)


def _second_client() -> AsyncClient:
    return AsyncClient(transport=ASGITransport(app=app), base_url="https://testserver")


async def _login_admin(client, make_admin, fetch_csrf, email="owner@example.com") -> str:
    return await login_admin(client, make_admin, fetch_csrf, email=email)


async def _setup_member(
    admin_client,
    make_admin,
    fetch_csrf,
    monkeypatch,
    *,
    email: str,
    admin_token: str,
    visibility: str | None = None,
):
    member_client = _second_client()
    capture = capture_onboarding_token(monkeypatch)
    readable_id, member_token = await onboard_member(
        member_client,
        admin_client,
        admin_token,
        capture,
        email=email,
        visibility=visibility,
    )
    return member_client, member_token, readable_id


async def _public_member(client, make_admin, fetch_csrf, monkeypatch, *, email):
    admin_token = await _login_admin(client, make_admin, fetch_csrf)
    member_client, token, readable = await _setup_member(
        client, make_admin, fetch_csrf, monkeypatch,
        email=email, admin_token=admin_token, visibility="public",
    )
    return member_client, token, readable, admin_token


# ---------------------------------------------------------------------------
# Submission lifecycle
# ---------------------------------------------------------------------------
async def test_submit_moves_draft_to_pending_review(client, make_admin, fetch_csrf, monkeypatch):
    admin_token = await _login_admin(client, make_admin, fetch_csrf)
    member_client, token, _ = await _setup_member(
        client, make_admin, fetch_csrf, monkeypatch,
        email="submit@example.com", admin_token=admin_token,
    )
    work = await create_work(member_client, token, title="Submit Me")

    submitted = await submit_work(member_client, token, work["id"])
    assert submitted["publication_status"] == "pending_review"
    assert submitted["submitted_at"] is not None
    assert submitted["review_feedback"] is None

    # Submitting again while pending is rejected.
    res = await member_client.post(
        f"/api/member/works/{work['id']}/submit",
        headers={"X-CSRF-Token": token},
    )
    assert res.status_code == 409
    assert res.json()["error"]["code"] == "REVIEW_ALREADY_PENDING"


async def test_submit_requires_csrf(client, make_admin, fetch_csrf, monkeypatch):
    admin_token = await _login_admin(client, make_admin, fetch_csrf)
    member_client, token, _ = await _setup_member(
        client, make_admin, fetch_csrf, monkeypatch,
        email="submitcsrf@example.com", admin_token=admin_token,
    )
    work = await create_work(member_client, token, title="No CSRF")
    res = await member_client.post(f"/api/member/works/{work['id']}/submit")
    assert res.status_code == 403


async def test_withdraw_pending_submission(client, make_admin, fetch_csrf, monkeypatch):
    admin_token = await _login_admin(client, make_admin, fetch_csrf)
    member_client, token, _ = await _setup_member(
        client, make_admin, fetch_csrf, monkeypatch,
        email="withdraw@example.com", admin_token=admin_token,
    )
    work = await create_work(member_client, token, title="Withdraw Me")
    await submit_work(member_client, token, work["id"])

    status, body = await withdraw_work(member_client, token, work["id"])
    assert status == 200, body
    assert body["publication_status"] == "draft"
    assert body["submitted_at"] is None

    # Withdrawing a draft is not allowed.
    status, body = await withdraw_work(member_client, token, work["id"])
    assert status == 409
    assert body["error"]["code"] == "NOT_AWAITING_REVIEW"


# ---------------------------------------------------------------------------
# Admin decisions
# ---------------------------------------------------------------------------
async def test_approve_publishes_and_exposes_public_work(client, make_admin, fetch_csrf, monkeypatch):
    member_client, token, readable, admin_token = await _public_member(
        client, make_admin, fetch_csrf, monkeypatch, email="approve@example.com"
    )
    work = await create_work(member_client, token, title="Approve Me", visibility="public")
    await submit_work(member_client, token, work["id"])

    # Pending review is never public.
    res = await client.get(f"/api/public/members/{readable}/works/{work['slug']}")
    assert res.status_code == 404

    # Admin queue surfaces it.
    listing = await client.get("/api/admin/works", params={"status": "pending_review"})
    assert listing.status_code == 200, listing.text
    assert work["id"] in [item["id"] for item in listing.json()["items"]]

    status, body = await review_work(client, admin_token, work["id"], "approve")
    assert status == 200, body
    assert body["publication_status"] == "published"
    assert body["reviewed_at"] is not None
    assert body["member_name"]

    res = await client.get(f"/api/public/members/{readable}/works/{work['slug']}")
    assert res.status_code == 200, res.text


async def test_request_changes_requires_feedback_then_resubmit(
    client, make_admin, fetch_csrf, monkeypatch
):
    admin_token = await _login_admin(client, make_admin, fetch_csrf)
    member_client, token, _ = await _setup_member(
        client, make_admin, fetch_csrf, monkeypatch,
        email="changes@example.com", admin_token=admin_token,
    )
    work = await create_work(member_client, token, title="Needs Work")
    await submit_work(member_client, token, work["id"])

    status, body = await review_work(client, admin_token, work["id"], "request_changes")
    assert status == 422
    assert body["error"]["code"] == "FEEDBACK_REQUIRED"

    status, body = await review_work(
        client, admin_token, work["id"], "request_changes", feedback="Add more detail"
    )
    assert status == 200, body
    assert body["publication_status"] == "changes_requested"
    assert body["review_feedback"] == "Add more detail"

    # The member can edit and resubmit; the previous feedback is cleared.
    await patch_work(member_client, token, work["id"], summary="Now with detail.")
    resubmitted = await submit_work(member_client, token, work["id"])
    assert resubmitted["publication_status"] == "pending_review"
    assert resubmitted["review_feedback"] is None

    status, body = await review_work(client, admin_token, work["id"], "approve")
    assert status == 200
    assert body["publication_status"] == "published"


async def test_reject_then_resubmit(client, make_admin, fetch_csrf, monkeypatch):
    admin_token = await _login_admin(client, make_admin, fetch_csrf)
    member_client, token, _ = await _setup_member(
        client, make_admin, fetch_csrf, monkeypatch,
        email="reject@example.com", admin_token=admin_token,
    )
    work = await create_work(member_client, token, title="Reject Me")
    await submit_work(member_client, token, work["id"])

    status, body = await review_work(
        client, admin_token, work["id"], "reject", feedback="Out of scope"
    )
    assert status == 200, body
    assert body["publication_status"] == "rejected"
    assert body["review_feedback"] == "Out of scope"

    resubmitted = await submit_work(member_client, token, work["id"])
    assert resubmitted["publication_status"] == "pending_review"


async def test_decision_requires_pending_review(client, make_admin, fetch_csrf, monkeypatch):
    admin_token = await _login_admin(client, make_admin, fetch_csrf)
    member_client, token, _ = await _setup_member(
        client, make_admin, fetch_csrf, monkeypatch,
        email="notpending@example.com", admin_token=admin_token,
    )
    work = await create_work(member_client, token, title="Still a draft")

    status, body = await review_work(client, admin_token, work["id"], "approve")
    assert status == 409
    assert body["error"]["code"] == "WORK_NOT_IN_REVIEW"


async def test_member_cannot_reach_admin_review(client, make_admin, fetch_csrf, monkeypatch):
    admin_token = await _login_admin(client, make_admin, fetch_csrf)
    member_client, token, _ = await _setup_member(
        client, make_admin, fetch_csrf, monkeypatch,
        email="noreach@example.com", admin_token=admin_token,
    )
    work = await create_work(member_client, token, title="Mine")
    await submit_work(member_client, token, work["id"])

    res = await member_client.get("/api/admin/works")
    assert res.status_code in (401, 403)

    res = await member_client.post(
        f"/api/admin/works/{work['id']}/decision",
        json={"action": "approve"},
        headers={"X-CSRF-Token": token},
    )
    assert res.status_code in (401, 403)


async def test_editor_cannot_decide(client, make_admin, fetch_csrf, monkeypatch):
    admin_token = await _login_admin(client, make_admin, fetch_csrf)
    member_client, token, _ = await _setup_member(
        client, make_admin, fetch_csrf, monkeypatch,
        email="editormember@example.com", admin_token=admin_token,
    )
    work = await create_work(member_client, token, title="Editor Check")
    await submit_work(member_client, token, work["id"])

    editor_token = await login_admin(
        client, make_admin, fetch_csrf, email="editor@example.com", role=Role.EDITOR
    )
    status, body = await review_work(client, editor_token, work["id"], "approve")
    assert status == 403


# ---------------------------------------------------------------------------
# Official featuring + public contributions
# ---------------------------------------------------------------------------
async def test_feature_requires_published(client, make_admin, fetch_csrf, monkeypatch):
    admin_token = await _login_admin(client, make_admin, fetch_csrf)
    member_client, token, _ = await _setup_member(
        client, make_admin, fetch_csrf, monkeypatch,
        email="featuredraft@example.com", admin_token=admin_token,
    )
    work = await create_work(member_client, token, title="Draft Feature", visibility="public")

    status, body = await feature_work(client, admin_token, work["id"], featured=True)
    assert status == 409
    assert body["error"]["code"] == "WORK_NOT_PUBLISHED"


async def test_feature_requires_public_visibility(client, make_admin, fetch_csrf, monkeypatch):
    admin_token = await _login_admin(client, make_admin, fetch_csrf)
    member_client, token, _ = await _setup_member(
        client, make_admin, fetch_csrf, monkeypatch,
        email="featureprivate@example.com", admin_token=admin_token,
    )
    work = await create_work(member_client, token, title="Private Feature")  # private visibility
    await publish_work(member_client, token, work["id"])

    status, body = await feature_work(client, admin_token, work["id"], featured=True)
    assert status == 409
    assert body["error"]["code"] == "WORK_NOT_PUBLIC"


async def test_featured_contribution_public_flow(client, make_admin, fetch_csrf, monkeypatch):
    member_client, token, readable, admin_token = await _public_member(
        client, make_admin, fetch_csrf, monkeypatch, email="contrib@example.com"
    )
    work = await create_work(member_client, token, title="Featured Contribution", visibility="public")
    await publish_work(member_client, token, work["id"])

    status, body = await feature_work(client, admin_token, work["id"], featured=True)
    assert status == 200, body
    assert body["featured_on_projects"] is True
    assert body["featured_classification"] == "member-contribution"
    assert body["featured_at"] is not None

    res = await client.get("/api/public/contributions")
    assert res.status_code == 200, res.text
    items = res.json()["items"]
    entry = next((i for i in items if i["slug"] == work["slug"]), None)
    assert entry is not None
    assert entry["author"]["member_id"] == readable
    assert entry["classification"] == "member-contribution"
    assert entry["title"] == "Featured Contribution"

    # Unfeaturing removes it from the official page.
    status, body = await feature_work(client, admin_token, work["id"], featured=False)
    assert status == 200, body
    assert body["featured_on_projects"] is False
    res = await client.get("/api/public/contributions")
    assert all(i["slug"] != work["slug"] for i in res.json()["items"])


async def test_featured_contribution_respects_private_profile(
    client, make_admin, fetch_csrf, monkeypatch
):
    """A featured work whose owner has a private profile stays private."""
    admin_token = await _login_admin(client, make_admin, fetch_csrf)
    member_client, token, readable = await _setup_member(
        client, make_admin, fetch_csrf, monkeypatch,
        email="featureprivprofile@example.com", admin_token=admin_token,  # private profile
    )
    work = await create_work(member_client, token, title="Should Stay Hidden", visibility="public")
    await publish_work(member_client, token, work["id"])

    status, body = await feature_work(client, admin_token, work["id"], featured=True)
    assert status == 200, body

    res = await client.get("/api/public/contributions")
    assert res.status_code == 200
    assert all(i["slug"] != work["slug"] for i in res.json()["items"])

    # And the work itself is not publicly reachable.
    res = await client.get(f"/api/public/members/{readable}/works/{work['slug']}")
    assert res.status_code == 404


async def test_feature_custom_classification(client, make_admin, fetch_csrf, monkeypatch):
    member_client, token, _readable, admin_token = await _public_member(
        client, make_admin, fetch_csrf, monkeypatch, email="classify@example.com"
    )
    work = await create_work(member_client, token, title="Classified", visibility="public")
    await publish_work(member_client, token, work["id"])

    status, body = await feature_work(
        client, admin_token, work["id"], featured=True, classification="experiment"
    )
    assert status == 200, body
    assert body["featured_classification"] == "experiment"

    res = await client.get("/api/public/contributions")
    entry = next(i for i in res.json()["items"] if i["slug"] == work["slug"])
    assert entry["classification"] == "experiment"


async def test_editor_cannot_feature(client, make_admin, fetch_csrf, monkeypatch):
    member_client, token, _readable, _admin_token = await _public_member(
        client, make_admin, fetch_csrf, monkeypatch, email="editormember2@example.com"
    )
    work = await create_work(member_client, token, title="Editor Feature", visibility="public")
    await publish_work(member_client, token, work["id"])

    editor_token = await login_admin(
        client, make_admin, fetch_csrf, email="editor2@example.com", role=Role.EDITOR
    )
    status, body = await feature_work(client, editor_token, work["id"], featured=True)
    assert status == 403
