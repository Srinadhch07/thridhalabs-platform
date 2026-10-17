"""Certificate issuance, verification, delivery and revocation tests.

Covers RBAC + CSRF, the approve-on-issue flow, idempotent/concurrent issuance,
id format + uniqueness, PDF download integrity, QR decoding (from the actual
PDF), public verification (issued/revoked/unknown/private work), email delivery
(success + failure), storage/URL failure handling, and member isolation.
"""

from __future__ import annotations

import asyncio
import io
import re

import cv2
import numpy as np
import pypdf
from httpx import ASGITransport, AsyncClient
from PIL import Image

from app.main import app
from app.models.admin import Role
from tests._content_helpers import (
    apply_certification,
    capture_certificate_email,
    capture_onboarding_token,
    create_work,
    email_certificate,
    issue_certificate,
    login_admin,
    onboard_member,
    patch_work,
    publish_work,
    revoke_certificate,
)

CERT_ID_RE = re.compile(r"^THL-CERT-\d{4}-[ABCDEFGHJKLMNPQRSTUVWXYZ23456789]{12}$")
EXPECTED_BASE = "https://thridhalabs.test"


def _second_client() -> AsyncClient:
    return AsyncClient(transport=ASGITransport(app=app), base_url="https://testserver")


class _Ctx:
    pass


async def _ready(
    client,
    make_admin,
    fetch_csrf,
    monkeypatch,
    *,
    email: str,
    visibility: str | None = None,
    work_visibility: str = "private",
) -> _Ctx:
    """Set up an approved-able certification request owned by a fresh member."""
    admin_token = await login_admin(client, make_admin, fetch_csrf)
    member_client = _second_client()
    capture = capture_onboarding_token(monkeypatch)
    readable, member_token = await onboard_member(
        member_client,
        client,
        admin_token,
        capture,
        email=email,
        visibility=visibility,
    )
    work = await create_work(
        member_client, member_token, title="Certificate Work", visibility=work_visibility
    )
    await publish_work(member_client, member_token, work["id"])
    status, body = await apply_certification(member_client, member_token, work["id"])
    assert status == 201, body

    ctx = _Ctx()
    ctx.admin_token = admin_token
    ctx.member_client = member_client
    ctx.member_token = member_token
    ctx.readable = readable
    ctx.work = work
    ctx.request_id = body["id"]
    ctx.email = email
    return ctx


async def _approve(client, admin_token: str, request_id: str) -> None:
    res = await client.post(
        f"/api/admin/certifications/{request_id}/decision",
        json={"action": "approve"},
        headers={"X-CSRF-Token": admin_token},
    )
    assert res.status_code == 200, res.text


async def _issue_ok(client, admin_token: str, request_id: str) -> dict:
    status, body = await issue_certificate(client, admin_token, request_id)
    assert status == 201, body
    return body


# ---------------------------------------------------------------------------
# RBAC / CSRF
# ---------------------------------------------------------------------------
async def test_issue_requires_authentication(client, fetch_csrf, make_admin, monkeypatch):
    token = await fetch_csrf()
    status, body = await issue_certificate(client, token, "000000000000000000000000")
    assert status == 401, body


async def test_issue_requires_csrf(client, make_admin, fetch_csrf, monkeypatch):
    ctx = await _ready(client, make_admin, fetch_csrf, monkeypatch, email="r1@example.com")
    res = await client.post(
        "/api/admin/certificates", json={"request_id": ctx.request_id}
    )
    assert res.status_code == 403, res.text


async def test_editor_cannot_issue(client, make_admin, fetch_csrf, monkeypatch):
    ctx = await _ready(client, make_admin, fetch_csrf, monkeypatch, email="r2@example.com")
    editor_client = _second_client()
    await make_admin("editor@example.com", role=Role.EDITOR)
    csrf = await editor_client.get("/api/auth/csrf")
    login = await editor_client.post(
        "/api/auth/login",
        json={"email": "editor@example.com", "password": "CorrectHorse!Battery9"},
        headers={"X-CSRF-Token": csrf.json()["csrfToken"]},
    )
    assert login.status_code == 200, login.text
    editor_token = (await editor_client.get("/api/auth/csrf")).json()["csrfToken"]
    status, body = await issue_certificate(editor_client, editor_token, ctx.request_id)
    assert status == 403, body


async def test_member_cannot_issue_or_revoke(client, make_admin, fetch_csrf, monkeypatch):
    ctx = await _ready(client, make_admin, fetch_csrf, monkeypatch, email="r3@example.com")
    res = await ctx.member_client.post(
        "/api/admin/certificates",
        json={"request_id": ctx.request_id},
        headers={"X-CSRF-Token": ctx.member_token},
    )
    assert res.status_code in (401, 403), res.text
    res = await ctx.member_client.post(
        "/api/admin/certificates/THL-CERT-2026-ABCDEFGHJKLM/revoke",
        json={"reason": "nope"},
        headers={"X-CSRF-Token": ctx.member_token},
    )
    assert res.status_code in (401, 403), res.text


# ---------------------------------------------------------------------------
# Issuance flow + id
# ---------------------------------------------------------------------------
async def test_issue_from_submitted_auto_approves(client, make_admin, fetch_csrf, monkeypatch):
    ctx = await _ready(client, make_admin, fetch_csrf, monkeypatch, email="i1@example.com")
    body = await _issue_ok(client, ctx.admin_token, ctx.request_id)
    assert CERT_ID_RE.match(body["certificate_id"]), body
    assert body["status"] == "issued"
    assert body["email_status"] == "not_sent"
    assert body["verify_url"] == f"{EXPECTED_BASE}/verify-certificate/{body['certificate_id']}"

    detail = await client.get(f"/api/admin/certifications/{ctx.request_id}")
    assert detail.status_code == 200
    detail_body = detail.json()
    assert detail_body["status"] == "approved"
    assert detail_body["certificate"]["certificate_id"] == body["certificate_id"]


async def test_issue_for_already_approved(client, make_admin, fetch_csrf, monkeypatch):
    ctx = await _ready(client, make_admin, fetch_csrf, monkeypatch, email="i2@example.com")
    await _approve(client, ctx.admin_token, ctx.request_id)
    body = await _issue_ok(client, ctx.admin_token, ctx.request_id)
    assert body["status"] == "issued"


async def test_issue_rejected_request_conflicts(client, make_admin, fetch_csrf, monkeypatch):
    ctx = await _ready(client, make_admin, fetch_csrf, monkeypatch, email="i3@example.com")
    res = await client.post(
        f"/api/admin/certifications/{ctx.request_id}/decision",
        json={"action": "reject", "feedback": "Not eligible"},
        headers={"X-CSRF-Token": ctx.admin_token},
    )
    assert res.status_code == 200, res.text
    status, body = await issue_certificate(client, ctx.admin_token, ctx.request_id)
    assert status == 409
    assert body["error"]["code"] == "CERTIFICATION_NOT_APPROVED"


async def test_issue_unknown_request_404(client, make_admin, fetch_csrf, monkeypatch):
    ctx = await _ready(client, make_admin, fetch_csrf, monkeypatch, email="i4@example.com")
    status, body = await issue_certificate(client, ctx.admin_token, "0" * 24)
    assert status == 404
    assert body["error"]["code"] == "CERTIFICATION_NOT_FOUND"


async def test_duplicate_issue_is_idempotent(client, make_admin, fetch_csrf, monkeypatch):
    ctx = await _ready(client, make_admin, fetch_csrf, monkeypatch, email="i5@example.com")
    first = await _issue_ok(client, ctx.admin_token, ctx.request_id)
    second = await _issue_ok(client, ctx.admin_token, ctx.request_id)
    assert first["certificate_id"] == second["certificate_id"]

    listing = await client.get("/api/admin/certificates")
    assert listing.json()["total"] == 1


async def test_concurrent_issue_yields_single_certificate(client, make_admin, fetch_csrf, monkeypatch):
    ctx = await _ready(client, make_admin, fetch_csrf, monkeypatch, email="i6@example.com")
    await _approve(client, ctx.admin_token, ctx.request_id)

    results = await asyncio.gather(
        issue_certificate(client, ctx.admin_token, ctx.request_id),
        issue_certificate(client, ctx.admin_token, ctx.request_id),
    )
    assert [status for status, _ in results] == [201, 201], results
    ids = {body["certificate_id"] for _, body in results}
    assert len(ids) == 1, ids

    listing = await client.get("/api/admin/certificates")
    assert listing.json()["total"] == 1


async def test_certificate_ids_are_unique_and_well_formed(client, make_admin, fetch_csrf, monkeypatch):
    ctx_a = await _ready(client, make_admin, fetch_csrf, monkeypatch, email="u1@example.com")
    a = await _issue_ok(client, ctx_a.admin_token, ctx_a.request_id)

    # A second, independent certification request + certificate.
    work = await create_work(ctx_a.member_client, ctx_a.member_token, title="Second Work")
    await publish_work(ctx_a.member_client, ctx_a.member_token, work["id"])
    _, applied = await apply_certification(ctx_a.member_client, ctx_a.member_token, work["id"])
    b = await _issue_ok(client, ctx_a.admin_token, applied["id"])

    assert a["certificate_id"] != b["certificate_id"]
    assert CERT_ID_RE.match(b["certificate_id"])


# ---------------------------------------------------------------------------
# Listing / reading
# ---------------------------------------------------------------------------
async def test_admin_list_filters(client, make_admin, fetch_csrf, monkeypatch):
    ctx = await _ready(client, make_admin, fetch_csrf, monkeypatch, email="l1@example.com")
    cert = await _issue_ok(client, ctx.admin_token, ctx.request_id)

    by_request = await client.get(
        "/api/admin/certificates", params={"request_id": ctx.request_id}
    )
    assert by_request.json()["total"] == 1

    issued = await client.get("/api/admin/certificates", params={"status": "issued"})
    assert issued.json()["total"] == 1
    revoked = await client.get("/api/admin/certificates", params={"status": "revoked"})
    assert revoked.json()["total"] == 0
    assert cert["certificate_id"] in {item["certificate_id"] for item in issued.json()["items"]}


async def test_member_lists_and_gets_own_certificate(client, make_admin, fetch_csrf, monkeypatch):
    ctx = await _ready(client, make_admin, fetch_csrf, monkeypatch, email="m1@example.com")
    cert = await _issue_ok(client, ctx.admin_token, ctx.request_id)

    listing = await ctx.member_client.get("/api/member/certificates")
    assert listing.status_code == 200
    assert listing.json()["total"] == 1

    one = await ctx.member_client.get(f"/api/member/certificates/{cert['certificate_id']}")
    assert one.status_code == 200
    assert one.json()["certificate_id"] == cert["certificate_id"]
    assert "issued_by" not in one.json()


async def test_member_cannot_access_other_certificate(client, make_admin, fetch_csrf, monkeypatch):
    ctx = await _ready(client, make_admin, fetch_csrf, monkeypatch, email="m2@example.com")
    cert = await _issue_ok(client, ctx.admin_token, ctx.request_id)

    other_client = _second_client()
    capture = capture_onboarding_token(monkeypatch)
    _r, other_token = await onboard_member(
        other_client, client, ctx.admin_token, capture, email="m2-other@example.com"
    )
    got = await other_client.get(f"/api/member/certificates/{cert['certificate_id']}")
    assert got.status_code == 404
    dl = await other_client.get(f"/api/member/certificates/{cert['certificate_id']}/download")
    assert dl.status_code == 404


# ---------------------------------------------------------------------------
# PDF + QR
# ---------------------------------------------------------------------------
async def test_download_pdf_is_valid(client, make_admin, fetch_csrf, monkeypatch):
    ctx = await _ready(client, make_admin, fetch_csrf, monkeypatch, email="p1@example.com")
    cert = await _issue_ok(client, ctx.admin_token, ctx.request_id)

    res = await client.get(f"/api/admin/certificates/{cert['certificate_id']}/download")
    assert res.status_code == 200, res.text
    assert res.headers["content-type"].startswith("application/pdf")
    assert res.content.startswith(b"%PDF-")
    assert cert["certificate_id"] in res.headers["content-disposition"]

    reader = pypdf.PdfReader(io.BytesIO(res.content))
    assert len(reader.pages) == 1
    text = reader.pages[0].extract_text()
    assert cert["certificate_id"] in text


async def test_qr_in_pdf_decodes_to_verification_url(client, make_admin, fetch_csrf, monkeypatch):
    ctx = await _ready(client, make_admin, fetch_csrf, monkeypatch, email="p2@example.com")
    cert = await _issue_ok(client, ctx.admin_token, ctx.request_id)

    res = await client.get(f"/api/admin/certificates/{cert['certificate_id']}/download")
    reader = pypdf.PdfReader(io.BytesIO(res.content))
    images = list(reader.pages[0].images)
    assert images, "expected the QR image to be embedded in the PDF"

    detector = cv2.QRCodeDetector()
    decoded = set()
    for image in images:
        array = np.array(Image.open(io.BytesIO(image.data)).convert("RGB"))
        data, _points, _ = detector.detectAndDecode(array)
        if data:
            decoded.add(data)

    expected = f"{EXPECTED_BASE}/verify-certificate/{cert['certificate_id']}"
    assert expected in decoded, decoded


# ---------------------------------------------------------------------------
# Public verification
# ---------------------------------------------------------------------------
async def test_public_verify_issued_includes_work_url(client, make_admin, fetch_csrf, monkeypatch):
    ctx = await _ready(
        client, make_admin, fetch_csrf, monkeypatch,
        email="v1@example.com", visibility="public", work_visibility="public",
    )
    cert = await _issue_ok(client, ctx.admin_token, ctx.request_id)

    res = await client.get(f"/api/public/certificates/{cert['certificate_id']}")
    assert res.status_code == 200, res.text
    body = res.json()
    assert body["status"] == "issued"
    assert body["work_title"] == "Certificate Work"
    assert body["member_name"]
    assert body["work_url"] == f"{EXPECTED_BASE}/members/{ctx.readable}/works/{ctx.work['slug']}"
    # No private data leaks.
    assert "email" not in body and "member_id" not in body and "pdf_object_key" not in body


async def test_public_verify_hides_work_when_profile_private(client, make_admin, fetch_csrf, monkeypatch):
    ctx = await _ready(client, make_admin, fetch_csrf, monkeypatch, email="v2@example.com")
    cert = await _issue_ok(client, ctx.admin_token, ctx.request_id)
    body = (await client.get(f"/api/public/certificates/{cert['certificate_id']}")).json()
    assert body["work_url"] is None


async def test_public_verify_unknown_404(client):
    res = await client.get("/api/public/certificates/THL-CERT-2026-ZZZZZZZZZZZZ")
    assert res.status_code == 404


async def test_public_verify_revoked_shows_reason(client, make_admin, fetch_csrf, monkeypatch):
    ctx = await _ready(client, make_admin, fetch_csrf, monkeypatch, email="v3@example.com")
    cert = await _issue_ok(client, ctx.admin_token, ctx.request_id)
    status, _ = await revoke_certificate(
        client, ctx.admin_token, cert["certificate_id"], reason="Issued in error"
    )
    assert status == 200

    res = await client.get(f"/api/public/certificates/{cert['certificate_id']}")
    body = res.json()
    assert body["status"] == "revoked"
    assert body["revoked_at"] is not None
    assert body["revocation_reason"] == "Issued in error"


# ---------------------------------------------------------------------------
# Public verification — certified work presentation
# ---------------------------------------------------------------------------
async def test_public_verify_includes_certified_work(client, make_admin, fetch_csrf, monkeypatch):
    ctx = await _ready(
        client, make_admin, fetch_csrf, monkeypatch,
        email="w1@example.com", visibility="public", work_visibility="public",
    )
    cert = await _issue_ok(client, ctx.admin_token, ctx.request_id)

    res = await client.get(f"/api/public/certificates/{cert['certificate_id']}")
    assert res.status_code == 200, res.text
    body = res.json()
    work = body["work"]
    assert work is not None
    assert work["title"] == "Certificate Work"
    assert work["summary"] == "A short summary."
    assert isinstance(work["content"]["blocks"], list)
    assert work["author"]["member_id"] == ctx.readable
    assert work["author"]["display_name"]
    assert work["member_profile_url"] == f"{EXPECTED_BASE}/members/{ctx.readable}"
    assert work["current_work_url"] == (
        f"{EXPECTED_BASE}/members/{ctx.readable}/works/{ctx.work['slug']}"
    )
    assert work["has_newer_version"] is False
    assert work["certified_at"]
    # The projection never leaks private fields.
    assert "email" not in work["author"]
    assert "pdf_object_key" not in body
    assert "member_id" not in body


async def test_public_verify_work_snapshot_unchanged_after_edit(
    client, make_admin, fetch_csrf, monkeypatch
):
    ctx = await _ready(
        client, make_admin, fetch_csrf, monkeypatch,
        email="w2@example.com", visibility="public", work_visibility="public",
    )
    cert = await _issue_ok(client, ctx.admin_token, ctx.request_id)

    # Edit the work after certification: title (and therefore slug) + summary.
    await patch_work(
        ctx.member_client, ctx.member_token, ctx.work["id"],
        title="Renamed Work", summary="Updated summary.",
    )

    body = (await client.get(f"/api/public/certificates/{cert['certificate_id']}")).json()
    work = body["work"]
    # The presentation still shows the reviewed snapshot, not the latest edit.
    assert work["title"] == "Certificate Work"
    assert work["summary"] == "A short summary."
    assert work["has_newer_version"] is True
    # The current-version link tracks the renamed slug (id-based lookup).
    assert work["current_work_url"].endswith("/works/renamed-work")
    assert body["work_url"] == work["current_work_url"]
    # The frozen certificate title is untouched.
    assert body["work_title"] == "Certificate Work"


async def test_public_verify_omits_work_when_profile_private(
    client, make_admin, fetch_csrf, monkeypatch
):
    ctx = await _ready(client, make_admin, fetch_csrf, monkeypatch, email="w3@example.com")
    cert = await _issue_ok(client, ctx.admin_token, ctx.request_id)
    body = (await client.get(f"/api/public/certificates/{cert['certificate_id']}")).json()
    assert body["work"] is None
    assert body["work_url"] is None


async def test_public_verify_omits_work_when_unpublished(
    client, make_admin, fetch_csrf, monkeypatch
):
    ctx = await _ready(
        client, make_admin, fetch_csrf, monkeypatch,
        email="w4@example.com", visibility="public", work_visibility="public",
    )
    cert = await _issue_ok(client, ctx.admin_token, ctx.request_id)

    res = await ctx.member_client.post(
        f"/api/member/works/{ctx.work['id']}/unpublish",
        headers={"X-CSRF-Token": ctx.member_token},
    )
    assert res.status_code == 200, res.text

    body = (await client.get(f"/api/public/certificates/{cert['certificate_id']}")).json()
    assert body["work"] is None
    assert body["work_url"] is None


async def test_public_verify_omits_missing_snapshot(client, make_admin, fetch_csrf, monkeypatch):
    ctx = await _ready(
        client, make_admin, fetch_csrf, monkeypatch,
        email="w5@example.com", visibility="public", work_visibility="public",
    )
    cert = await _issue_ok(client, ctx.admin_token, ctx.request_id)

    from app.modules.certifications import repository as certifications_repository

    async def _missing(_request_id):
        return None

    monkeypatch.setattr(certifications_repository, "find_by_id", _missing)

    res = await client.get(f"/api/public/certificates/{cert['certificate_id']}")
    assert res.status_code == 200, res.text
    body = res.json()
    assert body["status"] == "issued"
    assert body["work"] is None
    # Verification still succeeds and reports the frozen title.
    assert body["work_title"] == "Certificate Work"


async def test_public_verify_revoked_still_includes_work(
    client, make_admin, fetch_csrf, monkeypatch
):
    ctx = await _ready(
        client, make_admin, fetch_csrf, monkeypatch,
        email="w6@example.com", visibility="public", work_visibility="public",
    )
    cert = await _issue_ok(client, ctx.admin_token, ctx.request_id)
    await revoke_certificate(
        client, ctx.admin_token, cert["certificate_id"], reason="Issued in error"
    )

    body = (await client.get(f"/api/public/certificates/{cert['certificate_id']}")).json()
    assert body["status"] == "revoked"
    assert body["work"] is not None
    assert body["work"]["title"] == "Certificate Work"


async def test_issue_fails_when_verify_url_not_configured(client, make_admin, fetch_csrf, monkeypatch):
    ctx = await _ready(client, make_admin, fetch_csrf, monkeypatch, email="v4@example.com")
    from types import SimpleNamespace

    monkeypatch.setattr(
        "app.modules.certificates.service.get_settings",
        lambda: SimpleNamespace(verification_base_url=None, APP_NAME="Thridha Labs"),
    )
    status, body = await issue_certificate(client, ctx.admin_token, ctx.request_id)
    assert status == 503
    assert body["error"]["code"] == "CERTIFICATE_URL_NOT_CONFIGURED"

    listing = await client.get("/api/admin/certificates")
    assert listing.json()["total"] == 0


async def test_issue_fails_when_localhost_configured(client, make_admin, fetch_csrf, monkeypatch):
    ctx = await _ready(client, make_admin, fetch_csrf, monkeypatch, email="v5@example.com")
    from types import SimpleNamespace

    monkeypatch.setattr(
        "app.modules.certificates.service.get_settings",
        lambda: SimpleNamespace(
            verification_base_url="http://localhost:5173", APP_NAME="Thridha Labs"
        ),
    )
    status, body = await issue_certificate(client, ctx.admin_token, ctx.request_id)
    assert status == 503
    assert body["error"]["code"] == "CERTIFICATE_URL_NOT_CONFIGURED"


# ---------------------------------------------------------------------------
# Storage failure
# ---------------------------------------------------------------------------
async def test_storage_failure_does_not_issue(client, make_admin, fetch_csrf, monkeypatch):
    ctx = await _ready(client, make_admin, fetch_csrf, monkeypatch, email="s1@example.com")

    class _FailingProvider:
        mode = "local"

        async def put(self, *a, **k):
            from app.storage.base import StorageError

            raise StorageError("boom")

        async def get(self, *a, **k):  # pragma: no cover
            raise AssertionError("not called")

        async def delete(self, *a, **k):
            return None

        async def exists(self, *a, **k):  # pragma: no cover
            return False

        def url(self, key):  # pragma: no cover
            return key

    monkeypatch.setattr(
        "app.modules.certificates.service.get_storage_provider",
        lambda: _FailingProvider(),
    )
    status, body = await issue_certificate(client, ctx.admin_token, ctx.request_id)
    assert status == 500
    assert body["error"]["code"] == "STORAGE_ERROR"

    listing = await client.get("/api/admin/certificates")
    assert listing.json()["total"] == 0


# ---------------------------------------------------------------------------
# Revocation
# ---------------------------------------------------------------------------
async def test_revoke_requires_reason_and_admin(client, make_admin, fetch_csrf, monkeypatch):
    ctx = await _ready(client, make_admin, fetch_csrf, monkeypatch, email="rv1@example.com")
    cert = await _issue_ok(client, ctx.admin_token, ctx.request_id)

    empty = await client.post(
        f"/api/admin/certificates/{cert['certificate_id']}/revoke",
        json={"reason": ""},
        headers={"X-CSRF-Token": ctx.admin_token},
    )
    assert empty.status_code == 422, empty.text

    no_csrf = await client.post(
        f"/api/admin/certificates/{cert['certificate_id']}/revoke",
        json={"reason": "Because"},
    )
    assert no_csrf.status_code == 403, no_csrf.text

    member_try = await ctx.member_client.post(
        f"/api/admin/certificates/{cert['certificate_id']}/revoke",
        json={"reason": "Because"},
        headers={"X-CSRF-Token": ctx.member_token},
    )
    assert member_try.status_code in (401, 403)


async def test_revoke_then_still_downloadable_and_idempotent(
    client, make_admin, fetch_csrf, monkeypatch
):
    ctx = await _ready(client, make_admin, fetch_csrf, monkeypatch, email="rv2@example.com")
    cert = await _issue_ok(client, ctx.admin_token, ctx.request_id)

    status, body = await revoke_certificate(
        client, ctx.admin_token, cert["certificate_id"], reason="Issued in error"
    )
    assert status == 200, body
    assert body["status"] == "revoked"
    assert body["revoked_at"] is not None

    again = await revoke_certificate(
        client, ctx.admin_token, cert["certificate_id"], reason="Again"
    )
    assert again[0] == 409
    assert again[1]["error"]["code"] == "CERTIFICATE_ALREADY_REVOKED"

    # Revoked certificates remain downloadable (record is never deleted).
    dl = await client.get(f"/api/admin/certificates/{cert['certificate_id']}/download")
    assert dl.status_code == 200
    assert dl.content.startswith(b"%PDF-")


async def test_reissue_after_revoke_returns_revoked_certificate(
    client, make_admin, fetch_csrf, monkeypatch
):
    ctx = await _ready(client, make_admin, fetch_csrf, monkeypatch, email="rv3@example.com")
    cert = await _issue_ok(client, ctx.admin_token, ctx.request_id)
    await revoke_certificate(client, ctx.admin_token, cert["certificate_id"], reason="Oops")

    again = await _issue_ok(client, ctx.admin_token, ctx.request_id)
    assert again["certificate_id"] == cert["certificate_id"]
    assert again["status"] == "revoked"  # never reissued / never reused


# ---------------------------------------------------------------------------
# Email delivery
# ---------------------------------------------------------------------------
async def test_email_sends_attachment(client, make_admin, fetch_csrf, monkeypatch):
    ctx = await _ready(client, make_admin, fetch_csrf, monkeypatch, email="e1@example.com")
    cert = await _issue_ok(client, ctx.admin_token, ctx.request_id)
    capture = capture_certificate_email(monkeypatch)

    status, body = await email_certificate(client, ctx.admin_token, cert["certificate_id"])
    assert status == 200, body
    assert body["email_status"] == "sent"
    assert len(capture["messages"]) == 1
    message = capture["messages"][0]
    assert message["to"] == "e1@example.com"
    assert len(message["attachments"]) == 1
    attachment = message["attachments"][0]
    assert attachment.filename == cert["pdf_filename"]
    assert attachment.content.startswith(b"%PDF-")


async def test_email_failure_recorded_but_certificate_valid(
    client, make_admin, fetch_csrf, monkeypatch
):
    ctx = await _ready(client, make_admin, fetch_csrf, monkeypatch, email="e2@example.com")
    cert = await _issue_ok(client, ctx.admin_token, ctx.request_id)
    capture_certificate_email(monkeypatch, fail=True)

    status, body = await email_certificate(client, ctx.admin_token, cert["certificate_id"])
    assert status == 502
    assert body["error"]["code"] == "CERTIFICATE_EMAIL_FAILED"

    detail = await client.get(f"/api/admin/certificates/{cert['certificate_id']}")
    assert detail.status_code == 200
    assert detail.json()["email_status"] == "failed"
    assert detail.json()["email_attempts"] == 1

    # Still valid + downloadable.
    public = await client.get(f"/api/public/certificates/{cert['certificate_id']}")
    assert public.json()["status"] == "issued"
    dl = await client.get(f"/api/admin/certificates/{cert['certificate_id']}/download")
    assert dl.status_code == 200
