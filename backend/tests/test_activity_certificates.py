"""Activity-certificate issuance, verification, delivery and revocation tests.

Covers RBAC + CSRF, server-side eligibility, id format, idempotent issuance vs.
distinct awards, PDF download integrity, QR decoding (from the actual PDF),
public verification (issued/revoked/unknown/public work), email delivery
(success + failure), the independent template, member isolation and the
invariant that the Work Recognition `certificates` collection is never touched.
"""

from __future__ import annotations

import io
import re

import cv2
import numpy as np
import pypdf
from httpx import ASGITransport, AsyncClient

from app.main import app
from app.models.admin import Role
from tests._content_helpers import (
    capture_onboarding_token,
    create_activity,
    create_work,
    login_admin,
    member_login,
    onboard_member,
    publish_activity,
    publish_work,
    register_activity,
    withdraw_activity,
)

CERT_ID_RE = re.compile(r"^THL-ACT-CERT-\d{4}-[ABCDEFGHJKLMNPQRSTUVWXYZ23456789]{12}$")
EXPECTED_BASE = "https://thridhalabs.test"


def _second_client() -> AsyncClient:
    return AsyncClient(transport=ASGITransport(app=app), base_url="https://testserver")


class _Ctx:
    pass


async def _setup(
    client,
    make_admin,
    fetch_csrf,
    monkeypatch,
    *,
    email: str,
    activity_type: str = "hackathon",
    visibility: str | None = None,
) -> _Ctx:
    """An owner admin, a published activity and one confirmed participant."""
    ctx = _Ctx()
    ctx.admin_token = await login_admin(client, make_admin, fetch_csrf)
    ctx.activity = await create_activity(
        client, ctx.admin_token, title="Atlas Hack", activity_type=activity_type
    )
    await publish_activity(client, ctx.admin_token, ctx.activity["id"])

    ctx.member_client = _second_client()
    capture = capture_onboarding_token(monkeypatch)
    ctx.readable, ctx.member_token = await onboard_member(
        ctx.member_client,
        client,
        ctx.admin_token,
        capture,
        email=email,
        visibility=visibility,
    )
    status, body = await register_activity(
        ctx.member_client, ctx.member_token, ctx.activity["slug"]
    )
    assert status in (200, 201), body

    eligible = await client.get(
        "/api/admin/activity-certificates/eligible",
        params={"activity_id": ctx.activity["id"]},
    )
    assert eligible.status_code == 200, eligible.text
    item = next(
        i
        for i in eligible.json()["items"]
        if i["member_readable_id"] == ctx.readable
    )
    ctx.member_id = item["member_id"]
    ctx.email = email
    return ctx


async def _issue(client, token: str, activity_id: str, member_id: str, **overrides):
    payload = {
        "activity_id": activity_id,
        "member_id": member_id,
        "award_category": "participation",
    }
    payload.update(overrides)
    res = await client.post(
        "/api/admin/activity-certificates",
        json=payload,
        headers={"X-CSRF-Token": token},
    )
    return res.status_code, res.json()


def _capture_cert_email(monkeypatch, *, fail: bool = False) -> dict:
    captured: dict = {"messages": [], "failed": fail}

    async def _fake_send(*, to, subject, text, attachments=()):  # noqa: ANN001
        if captured["failed"]:
            from app.services.email import EmailDeliveryError

            raise EmailDeliveryError("simulated delivery failure")
        captured["messages"].append(
            {"to": to, "subject": subject, "text": text, "attachments": attachments}
        )

    monkeypatch.setattr(
        "app.modules.activity_certificates.service.send_email", _fake_send
    )
    return captured


# ---------------------------------------------------------------------------
# RBAC / CSRF
# ---------------------------------------------------------------------------
async def test_issue_requires_authentication(client, fetch_csrf):
    await fetch_csrf()
    res = await client.post(
        "/api/admin/activity-certificates",
        json={"activity_id": "0" * 24, "member_id": "0" * 24},
    )
    assert res.status_code in (401, 403), res.text


async def test_issue_requires_csrf(client, make_admin, fetch_csrf, monkeypatch):
    ctx = await _setup(client, make_admin, fetch_csrf, monkeypatch, email="a1@example.com")
    res = await client.post(
        "/api/admin/activity-certificates",
        json={"activity_id": ctx.activity["id"], "member_id": ctx.member_id},
    )
    assert res.status_code == 403, res.text


async def test_editor_cannot_issue(client, make_admin, fetch_csrf, monkeypatch):
    ctx = await _setup(client, make_admin, fetch_csrf, monkeypatch, email="a2@example.com")
    await make_admin("editor-ac@example.com", role=Role.EDITOR)
    editor_client = _second_client()
    csrf = await editor_client.get("/api/auth/csrf")
    login = await editor_client.post(
        "/api/auth/login",
        json={"email": "editor-ac@example.com", "password": "CorrectHorse!Battery9"},
        headers={"X-CSRF-Token": csrf.json()["csrfToken"]},
    )
    assert login.status_code == 200, login.text
    token = (await editor_client.get("/api/auth/csrf")).json()["csrfToken"]

    status, body = await _issue(
        editor_client, token, ctx.activity["id"], ctx.member_id
    )
    assert status == 403, body


# ---------------------------------------------------------------------------
# Issuance + eligibility
# ---------------------------------------------------------------------------
async def test_issue_for_confirmed_participant(client, make_admin, fetch_csrf, monkeypatch):
    ctx = await _setup(client, make_admin, fetch_csrf, monkeypatch, email="b1@example.com")
    status, body = await _issue(client, ctx.admin_token, ctx.activity["id"], ctx.member_id)
    assert status == 201, body
    assert CERT_ID_RE.match(body["certificate_id"]), body
    assert body["status"] == "issued"
    assert body["award_category"] == "participation"
    assert body["award_label"] == "Participation"
    assert body["activity_title"] == "Atlas Hack"
    assert body["verify_url"] == (
        f"{EXPECTED_BASE}/verify-activity-certificate/{body['certificate_id']}"
    )
    assert body["email_status"] == "not_sent"
    assert body["download_path"] == (
        f"/admin/activity-certificates/{body['certificate_id']}/download"
    )


async def test_issue_rejects_withdrawn_participant(
    client, make_admin, fetch_csrf, monkeypatch
):
    ctx = await _setup(client, make_admin, fetch_csrf, monkeypatch, email="b2@example.com")
    await withdraw_activity(ctx.member_client, ctx.member_token, ctx.activity["slug"])
    status, body = await _issue(client, ctx.admin_token, ctx.activity["id"], ctx.member_id)
    assert status == 409, body
    assert body["error"]["code"] == "PARTICIPANT_NOT_ELIGIBLE"


async def test_unknown_activity_404(client, make_admin, fetch_csrf, monkeypatch):
    ctx = await _setup(client, make_admin, fetch_csrf, monkeypatch, email="b3@example.com")
    status, body = await _issue(client, ctx.admin_token, "0" * 24, ctx.member_id)
    assert status == 404
    assert body["error"]["code"] == "ACTIVITY_NOT_FOUND"


async def test_unknown_member_404(client, make_admin, fetch_csrf, monkeypatch):
    ctx = await _setup(client, make_admin, fetch_csrf, monkeypatch, email="b4@example.com")
    status, body = await _issue(client, ctx.admin_token, ctx.activity["id"], "0" * 24)
    assert status == 404
    assert body["error"]["code"] == "MEMBER_NOT_FOUND"


# ---------------------------------------------------------------------------
# Awards
# ---------------------------------------------------------------------------
async def test_custom_award_requires_label(client, make_admin, fetch_csrf, monkeypatch):
    ctx = await _setup(client, make_admin, fetch_csrf, monkeypatch, email="c1@example.com")
    status, body = await _issue(
        client, ctx.admin_token, ctx.activity["id"], ctx.member_id,
        award_category="custom",
    )
    assert status == 422, body
    assert body["error"]["code"] == "AWARD_LABEL_REQUIRED"


async def test_custom_award_with_label_and_statement(
    client, make_admin, fetch_csrf, monkeypatch
):
    ctx = await _setup(client, make_admin, fetch_csrf, monkeypatch, email="c2@example.com")
    status, body = await _issue(
        client, ctx.admin_token, ctx.activity["id"], ctx.member_id,
        award_category="custom",
        custom_award_label="Best Innovation",
        custom_statement="For the most inventive solution.",
    )
    assert status == 201, body
    assert body["award_category"] == "custom"
    assert body["award_label"] == "Best Innovation"
    assert body["award_statement"] == "For the most inventive solution."


async def test_duplicate_award_is_idempotent(client, make_admin, fetch_csrf, monkeypatch):
    ctx = await _setup(client, make_admin, fetch_csrf, monkeypatch, email="d1@example.com")
    first = await _issue(client, ctx.admin_token, ctx.activity["id"], ctx.member_id)
    assert first[0] == 201, first
    second = await _issue(client, ctx.admin_token, ctx.activity["id"], ctx.member_id)
    assert second[0] == 201, second
    assert second[1]["certificate_id"] == first[1]["certificate_id"]

    listing = await client.get("/api/admin/activity-certificates")
    assert listing.json()["total"] == 1


async def test_distinct_awards_allowed(client, make_admin, fetch_csrf, monkeypatch):
    ctx = await _setup(client, make_admin, fetch_csrf, monkeypatch, email="d2@example.com")
    participation = await _issue(
        client, ctx.admin_token, ctx.activity["id"], ctx.member_id,
        award_category="participation",
    )
    first = await _issue(
        client, ctx.admin_token, ctx.activity["id"], ctx.member_id,
        award_category="first_place",
    )
    assert participation[0] == 201 and first[0] == 201
    assert participation[1]["certificate_id"] != first[1]["certificate_id"]
    assert first[1]["award_label"] == "First Place"


# ---------------------------------------------------------------------------
# PDF + QR
# ---------------------------------------------------------------------------
async def test_download_pdf_and_qr(client, make_admin, fetch_csrf, monkeypatch):
    ctx = await _setup(client, make_admin, fetch_csrf, monkeypatch, email="p0@example.com")
    cert = (
        await _issue(client, ctx.admin_token, ctx.activity["id"], ctx.member_id)
    )[1]

    res = await client.get(
        f"/api/admin/activity-certificates/{cert['certificate_id']}/download"
    )
    assert res.status_code == 200, res.text
    assert res.content.startswith(b"%PDF-")
    assert cert["certificate_id"] in res.headers["content-disposition"]

    reader = pypdf.PdfReader(io.BytesIO(res.content))
    assert len(reader.pages) == 1
    text = reader.pages[0].extract_text()
    assert cert["certificate_id"] in text
    assert "Atlas Hack" in text

    decoded: set[str] = set()
    for page in reader.pages:
        for image in page.images:
            gray = cv2.imdecode(
                np.frombuffer(image.data, dtype=np.uint8), cv2.IMREAD_GRAYSCALE
            )
            if gray is None:
                continue
            data, _, _ = cv2.QRCodeDetector().detectAndDecode(gray)
            if data:
                decoded.add(data)
    expected = f"{EXPECTED_BASE}/verify-activity-certificate/{cert['certificate_id']}"
    assert expected in decoded, decoded


# ---------------------------------------------------------------------------
# Public verification
# ---------------------------------------------------------------------------
async def test_public_verify_issued_and_unknown(client, make_admin, fetch_csrf, monkeypatch):
    ctx = await _setup(client, make_admin, fetch_csrf, monkeypatch, email="v1@example.com")
    cert = (
        await _issue(client, ctx.admin_token, ctx.activity["id"], ctx.member_id)
    )[1]

    res = await client.get(f"/api/public/activity-certificates/{cert['certificate_id']}")
    assert res.status_code == 200, res.text
    body = res.json()
    assert body["status"] == "issued"
    assert body["activity_title"] == "Atlas Hack"
    assert body["award_label"] == "Participation"
    assert body["member_name"]
    assert "member_id" not in body
    assert "email" not in body
    assert "pdf_object_key" not in body

    missing = await client.get(
        "/api/public/activity-certificates/THL-ACT-CERT-2026-ZZZZZZZZZZZZ"
    )
    assert missing.status_code == 404


async def test_public_verify_revoked_shows_reason(
    client, make_admin, fetch_csrf, monkeypatch
):
    ctx = await _setup(client, make_admin, fetch_csrf, monkeypatch, email="v2@example.com")
    cert = (
        await _issue(client, ctx.admin_token, ctx.activity["id"], ctx.member_id)
    )[1]
    res = await client.post(
        f"/api/admin/activity-certificates/{cert['certificate_id']}/revoke",
        json={"reason": "Issued in error"},
        headers={"X-CSRF-Token": ctx.admin_token},
    )
    assert res.status_code == 200, res.text

    body = (
        await client.get(f"/api/public/activity-certificates/{cert['certificate_id']}")
    ).json()
    assert body["status"] == "revoked"
    assert body["revoked_at"] is not None
    assert body["revocation_reason"] == "Issued in error"


# ---------------------------------------------------------------------------
# Revocation
# ---------------------------------------------------------------------------
async def test_revoke_requires_reason_and_is_idempotent(
    client, make_admin, fetch_csrf, monkeypatch
):
    ctx = await _setup(client, make_admin, fetch_csrf, monkeypatch, email="r1@example.com")
    cert = (
        await _issue(client, ctx.admin_token, ctx.activity["id"], ctx.member_id)
    )[1]

    empty = await client.post(
        f"/api/admin/activity-certificates/{cert['certificate_id']}/revoke",
        json={"reason": ""},
        headers={"X-CSRF-Token": ctx.admin_token},
    )
    assert empty.status_code == 422, empty.text

    no_csrf = await client.post(
        f"/api/admin/activity-certificates/{cert['certificate_id']}/revoke",
        json={"reason": "Because"},
    )
    assert no_csrf.status_code == 403, no_csrf.text

    first = await client.post(
        f"/api/admin/activity-certificates/{cert['certificate_id']}/revoke",
        json={"reason": "Issued in error"},
        headers={"X-CSRF-Token": ctx.admin_token},
    )
    assert first.status_code == 200, first.text
    assert first.json()["status"] == "revoked"

    again = await client.post(
        f"/api/admin/activity-certificates/{cert['certificate_id']}/revoke",
        json={"reason": "Again"},
        headers={"X-CSRF-Token": ctx.admin_token},
    )
    assert again.status_code == 409
    assert again.json()["error"]["code"] == "ACTIVITY_CERTIFICATE_ALREADY_REVOKED"

    dl = await client.get(
        f"/api/admin/activity-certificates/{cert['certificate_id']}/download"
    )
    assert dl.status_code == 200
    assert dl.content.startswith(b"%PDF-")


async def test_audit_trail_records_actions(client, make_admin, fetch_csrf, monkeypatch):
    ctx = await _setup(client, make_admin, fetch_csrf, monkeypatch, email="r2@example.com")
    cert = (
        await _issue(client, ctx.admin_token, ctx.activity["id"], ctx.member_id)
    )[1]
    await client.post(
        f"/api/admin/activity-certificates/{cert['certificate_id']}/revoke",
        json={"reason": "Issued in error"},
        headers={"X-CSRF-Token": ctx.admin_token},
    )
    res = await client.get(
        f"/api/admin/activity-certificates/{cert['certificate_id']}/audit"
    )
    assert res.status_code == 200, res.text
    actions = [entry["action"] for entry in res.json()]
    assert "issued" in actions
    assert "revoked" in actions


# ---------------------------------------------------------------------------
# Bulk
# ---------------------------------------------------------------------------
async def test_bulk_per_item_results(client, make_admin, fetch_csrf, monkeypatch):
    ctx = await _setup(client, make_admin, fetch_csrf, monkeypatch, email="bk1@example.com")

    second_client = _second_client()
    capture = capture_onboarding_token(monkeypatch)
    readable2, _ = await onboard_member(
        second_client, client, ctx.admin_token, capture, email="bk2@example.com"
    )
    token2 = await member_login(second_client, "bk2@example.com")
    assert (await register_activity(second_client, token2, ctx.activity["slug"]))[0] in (200, 201)

    # Already issued for ctx.member_id.
    await _issue(client, ctx.admin_token, ctx.activity["id"], ctx.member_id)
    eligible = (
        await client.get(
            "/api/admin/activity-certificates/eligible",
            params={"activity_id": ctx.activity["id"]},
        )
    ).json()["items"]
    id2 = next(
        i["member_id"] for i in eligible if i["member_readable_id"] == readable2
    )

    res = await client.post(
        "/api/admin/activity-certificates/bulk",
        json={
            "activity_id": ctx.activity["id"],
            "award_category": "participation",
            "recipients": [
                {"member_id": ctx.member_id},
                {"member_id": id2},
                {"member_id": "0" * 24},
            ],
        },
        headers={"X-CSRF-Token": ctx.admin_token},
    )
    assert res.status_code == 200, res.text
    body = res.json()
    assert body["issued_count"] == 1
    assert body["skipped_count"] == 1
    assert body["failed_count"] == 1
    assert body["issued"][0]["award_label"] == "Participation"
    assert body["skipped"][0]["reason"]
    assert body["failed"][0]["reason"]


# ---------------------------------------------------------------------------
# Email
# ---------------------------------------------------------------------------
async def test_email_success_and_failure(client, make_admin, fetch_csrf, monkeypatch):
    ctx = await _setup(client, make_admin, fetch_csrf, monkeypatch, email="em1@example.com")
    cert = (
        await _issue(client, ctx.admin_token, ctx.activity["id"], ctx.member_id)
    )[1]

    capture = _capture_cert_email(monkeypatch)
    ok = await client.post(
        f"/api/admin/activity-certificates/{cert['certificate_id']}/email",
        headers={"X-CSRF-Token": ctx.admin_token},
    )
    assert ok.status_code == 200, ok.text
    assert ok.json()["email_status"] == "sent"
    assert len(capture["messages"]) == 1
    assert capture["messages"][0]["to"] == "em1@example.com"
    assert capture["messages"][0]["attachments"][0].content.startswith(b"%PDF-")

    _capture_cert_email(monkeypatch, fail=True)
    failure = await client.post(
        f"/api/admin/activity-certificates/{cert['certificate_id']}/email",
        headers={"X-CSRF-Token": ctx.admin_token},
    )
    assert failure.status_code == 502, failure.text
    assert failure.json()["error"]["code"] == "ACTIVITY_CERTIFICATE_EMAIL_FAILED"

    detail = await client.get(
        f"/api/admin/activity-certificates/{cert['certificate_id']}"
    )
    assert detail.json()["email_status"] == "failed"
    # A failed email still verifies and downloads.
    assert (
        await client.get(f"/api/public/activity-certificates/{cert['certificate_id']}")
    ).status_code == 200


# ---------------------------------------------------------------------------
# Template
# ---------------------------------------------------------------------------
async def test_template_get_and_update(client, make_admin, fetch_csrf, monkeypatch):
    token = await login_admin(client, make_admin, fetch_csrf)

    current = await client.get("/api/admin/activity-certificates/template")
    assert current.status_code == 200, current.text
    assert current.json()["heading"] == "Certificate of Achievement"

    updated = await client.put(
        "/api/admin/activity-certificates/template",
        json={
            "heading": "Certificate of Excellence",
            "presentation_line": "Awarded to",
            "award_line": "for achievement as",
            "scope_statement": "Independent activity verification.",
            "footer_note": "Atlas awards",
            "award_labels": {"first_place": "Champion"},
            "award_statements": {"first_place": "Won the top prize."},
        },
        headers={"X-CSRF-Token": token},
    )
    assert updated.status_code == 200, updated.text
    body = updated.json()
    assert body["heading"] == "Certificate of Excellence"
    assert body["award_labels"]["first_place"] == "Champion"
    assert body["award_statements"]["first_place"] == "Won the top prize."


async def test_template_update_requires_admin(client, make_admin, fetch_csrf, monkeypatch):
    ctx = await _setup(client, make_admin, fetch_csrf, monkeypatch, email="t1@example.com")
    res = await ctx.member_client.put(
        "/api/admin/activity-certificates/template",
        json={
            "heading": "Nope",
            "presentation_line": "Nope",
            "award_line": "Nope",
            "scope_statement": "Nope",
            "footer_note": "Nope",
        },
        headers={"X-CSRF-Token": ctx.member_token},
    )
    assert res.status_code in (401, 403), res.text


# ---------------------------------------------------------------------------
# Member surface + isolation
# ---------------------------------------------------------------------------
async def test_member_lists_own_and_other_denied(
    client, make_admin, fetch_csrf, monkeypatch
):
    ctx = await _setup(client, make_admin, fetch_csrf, monkeypatch, email="mm1@example.com")
    cert = (
        await _issue(client, ctx.admin_token, ctx.activity["id"], ctx.member_id)
    )[1]

    listing = await ctx.member_client.get("/api/member/activity-certificates")
    assert listing.status_code == 200, listing.text
    assert listing.json()["total"] == 1

    own = await ctx.member_client.get(
        f"/api/member/activity-certificates/{cert['certificate_id']}"
    )
    assert own.status_code == 200
    assert "pdf_object_key" not in own.json()

    other_client = _second_client()
    capture = capture_onboarding_token(monkeypatch)
    await onboard_member(
        other_client, client, ctx.admin_token, capture, email="mm2@example.com"
    )
    await member_login(other_client, "mm2@example.com")
    denied = await other_client.get(
        f"/api/member/activity-certificates/{cert['certificate_id']}"
    )
    assert denied.status_code == 404


# ---------------------------------------------------------------------------
# Work association
# ---------------------------------------------------------------------------
async def test_work_association_public_link(client, make_admin, fetch_csrf, monkeypatch):
    ctx = await _setup(
        client, make_admin, fetch_csrf, monkeypatch,
        email="wk1@example.com", visibility="public",
    )
    work = await create_work(
        ctx.member_client, ctx.member_token, title="Award Work", visibility="public"
    )
    await publish_work(ctx.member_client, ctx.member_token, work["id"])

    status, cert = await _issue(
        client, ctx.admin_token, ctx.activity["id"], ctx.member_id, work_id=work["id"]
    )
    assert status == 201, cert
    assert cert["work_title"] == "Award Work"

    body = (
        await client.get(f"/api/public/activity-certificates/{cert['certificate_id']}")
    ).json()
    assert body["work"] is not None
    assert body["work"]["title"] == "Award Work"
    assert body["work"]["url"] == (
        f"{EXPECTED_BASE}/members/{ctx.readable}/works/{work['slug']}"
    )


async def test_work_from_other_member_rejected(
    client, make_admin, fetch_csrf, monkeypatch
):
    ctx = await _setup(client, make_admin, fetch_csrf, monkeypatch, email="wk2@example.com")
    other_client = _second_client()
    capture = capture_onboarding_token(monkeypatch)
    _, other_token = await onboard_member(
        other_client, client, ctx.admin_token, capture, email="wk3@example.com"
    )
    other_work = await create_work(other_client, other_token, title="Someone Else")
    status, body = await _issue(
        client, ctx.admin_token, ctx.activity["id"], ctx.member_id,
        work_id=other_work["id"],
    )
    assert status == 404, body
    assert body["error"]["code"] == "WORK_NOT_FOUND"


async def test_work_certificates_collection_untouched(
    client, make_admin, fetch_csrf, monkeypatch
):
    from app.db.mongo import get_mongo

    ctx = await _setup(client, make_admin, fetch_csrf, monkeypatch, email="iso1@example.com")
    await _issue(client, ctx.admin_token, ctx.activity["id"], ctx.member_id)

    db = get_mongo().database
    assert await db.certificates.count_documents({}) == 0
    assert await db.activity_certificates.count_documents({}) == 1
