"""Shared helpers for Phase 4 content API tests (not collected by pytest)."""

from __future__ import annotations

import io

from PIL import Image

from app.models.admin import Role


def png_bytes(width: int = 32, height: int = 24, color: str = "blue") -> bytes:
    buf = io.BytesIO()
    Image.new("RGB", (width, height), color).save(buf, "PNG")
    return buf.getvalue()


async def login_admin(
    client, make_admin, fetch_csrf,
    email: str = "owner@example.com", role: Role = Role.OWNER,
) -> str:
    """Create an admin, log in (fresh double-submit CSRF pair), return a fresh
    CSRF token matching the current cookie."""
    await make_admin(email, role=role)
    token = await fetch_csrf()
    res = await client.post(
        "/api/auth/login",
        json={"email": email, "password": "CorrectHorse!Battery9"},
        headers={"X-CSRF-Token": token},
    )
    assert res.status_code == 200, res.text
    return await fetch_csrf()


async def upload_media(client, token: str, data: bytes | None = None) -> dict:
    res = await client.post(
        "/api/media",
        files={"file": ("pixel.png", data or png_bytes(), "image/png")},
        headers={"X-CSRF-Token": token},
    )
    assert res.status_code == 201, res.text
    return res.json()


async def create_client(client, token: str, **overrides) -> dict:
    payload = {"name": "Acme Motors"}
    payload.update(overrides)
    res = await client.post(
        "/api/clients", json=payload, headers={"X-CSRF-Token": token}
    )
    assert res.status_code == 201, res.text
    return res.json()


async def create_project(client, token: str, **overrides) -> dict:
    payload = {"name": "Labs Site", "project_type": "product"}
    payload.update(overrides)
    res = await client.post(
        "/api/projects", json=payload, headers={"X-CSRF-Token": token}
    )
    assert res.status_code == 201, res.text
    return res.json()


async def create_testimonial(client, token: str, **overrides) -> dict:
    payload = {"person_name": "Ada Lovelace", "testimonial_text": "Great work."}
    payload.update(overrides)
    res = await client.post(
        "/api/testimonials", json=payload, headers={"X-CSRF-Token": token}
    )
    assert res.status_code == 201, res.text
    return res.json()


async def enable_careers(client, token: str, **overrides) -> dict:
    payload = {"enabled": True}
    payload.update(overrides)
    res = await client.put(
        "/api/careers", json=payload, headers={"X-CSRF-Token": token}
    )
    assert res.status_code == 200, res.text
    return res.json()


async def create_opportunity(client, token: str, **overrides) -> dict:
    payload = {"title": "Lab Member", "type": "lab-member", "description": "Build things."}
    payload.update(overrides)
    res = await client.post(
        "/api/careers/opportunities", json=payload, headers={"X-CSRF-Token": token}
    )
    assert res.status_code == 201, res.text
    return res.json()


# ---------------------------------------------------------------------------
# Member account helpers (Phase 9)
# ---------------------------------------------------------------------------
MEMBER_PASSWORD = "MemberPass!2024"


def capture_onboarding_token(monkeypatch) -> dict:
    """Patch the email service so tests capture onboarding links without any
    network access. Returns a dict that receives a `token` key (parsed out of
    the setup URL) plus the raw messages list."""

    captured: dict = {"messages": [], "token": None}

    async def _fake_send(*, to: str, subject: str, text: str) -> None:
        captured["messages"].append({"to": to, "subject": subject, "text": text})
        marker = "token="
        if marker in text:
            captured["token"] = text.split(marker, 1)[1].split("\n", 1)[0].strip()

    monkeypatch.setattr("app.modules.members.service.send_email", _fake_send)
    return captured


async def create_member(client, token: str, *, email: str, **overrides) -> dict:
    payload = {"email": email}
    payload.update(overrides)
    res = await client.post(
        "/api/members", json=payload, headers={"X-CSRF-Token": token}
    )
    assert res.status_code == 201, res.text
    return res.json()


async def member_setup(client, setup_token: str, password: str = MEMBER_PASSWORD) -> None:
    csrf = await client.get("/api/member/csrf")
    assert csrf.status_code == 200, csrf.text
    res = await client.post(
        "/api/member/setup",
        json={"token": setup_token, "password": password},
        headers={"X-CSRF-Token": csrf.json()["csrfToken"]},
    )
    assert res.status_code == 200, res.text


async def member_login(
    client, email: str, password: str = MEMBER_PASSWORD
) -> str:
    """Log in as a member and return a fresh CSRF token matching the cookie."""
    csrf = await client.get("/api/member/csrf")
    assert csrf.status_code == 200, csrf.text
    res = await client.post(
        "/api/member/login",
        json={"email": email, "password": password},
        headers={"X-CSRF-Token": csrf.json()["csrfToken"]},
    )
    assert res.status_code == 200, res.text
    csrf = await client.get("/api/member/csrf")
    return csrf.json()["csrfToken"]


async def complete_member_profile(
    client, token: str, **overrides
) -> dict:
    """Complete the member-managed profile fields (full_name is admin-managed
    and set at creation, so it is not part of this payload)."""
    payload = {
        "bio": "Test engineer.",
        "skills": ["python"],
        "interests": ["testing"],
    }
    payload.update(overrides)
    res = await client.patch(
        "/api/member/profile", json=payload, headers={"X-CSRF-Token": token}
    )
    assert res.status_code == 200, res.text
    return res.json()


# ---------------------------------------------------------------------------
# Work showcase + certification helpers
# ---------------------------------------------------------------------------
async def onboard_member(
    member_client,
    admin_client,
    admin_token: str,
    capture: dict,
    *,
    email: str,
    full_name: str | None = "Member Person",
    visibility: str | None = None,
) -> tuple[str, str]:
    """Create a member (as admin), complete onboarding + login on the member
    client, optionally set profile visibility. Returns (readable_member_id,
    member_csrf_token)."""
    member = await create_member(
        admin_client, admin_token, email=email, full_name=full_name
    )
    await member_setup(member_client, capture["token"])
    token = await member_login(member_client, email)
    if visibility is not None:
        await complete_member_profile(
            member_client, token, profile_visibility=visibility
        )
    return member["member_id"], token


async def create_work(client, token: str, **overrides) -> dict:
    payload = {"title": "My First Work", "summary": "A short summary."}
    payload.update(overrides)
    res = await client.post(
        "/api/member/works", json=payload, headers={"X-CSRF-Token": token}
    )
    assert res.status_code == 201, res.text
    return res.json()


async def patch_work(client, token: str, work_id: str, **fields) -> dict:
    res = await client.patch(
        f"/api/member/works/{work_id}",
        json=fields,
        headers={"X-CSRF-Token": token},
    )
    assert res.status_code == 200, res.text
    return res.json()


async def publish_work(client, token: str, work_id: str) -> dict:
    res = await client.post(
        f"/api/member/works/{work_id}/publish",
        headers={"X-CSRF-Token": token},
    )
    assert res.status_code == 200, res.text
    return res.json()


async def upload_member_media(client, token: str, data: bytes | None = None) -> dict:
    res = await client.post(
        "/api/member/media",
        files={"file": ("pixel.png", data or png_bytes(), "image/png")},
        headers={"X-CSRF-Token": token},
    )
    assert res.status_code in (200, 201), res.text
    return res.json()


async def submit_work(client, token: str, work_id: str) -> dict:
    res = await client.post(
        f"/api/member/works/{work_id}/submit",
        headers={"X-CSRF-Token": token},
    )
    assert res.status_code == 200, res.text
    return res.json()


async def withdraw_work(client, token: str, work_id: str) -> tuple[int, dict]:
    res = await client.post(
        f"/api/member/works/{work_id}/withdraw",
        headers={"X-CSRF-Token": token},
    )
    return res.status_code, res.json()


async def review_work(
    client,
    token: str,
    work_id: str,
    action: str,
    feedback: str | None = None,
) -> tuple[int, dict]:
    body: dict = {"action": action}
    if feedback is not None:
        body["feedback"] = feedback
    res = await client.post(
        f"/api/admin/works/{work_id}/decision",
        json=body,
        headers={"X-CSRF-Token": token},
    )
    return res.status_code, res.json()


async def feature_work(
    client,
    token: str,
    work_id: str,
    *,
    featured: bool = True,
    classification: str | None = None,
) -> tuple[int, dict]:
    body: dict = {"featured": featured}
    if classification is not None:
        body["classification"] = classification
    res = await client.post(
        f"/api/admin/works/{work_id}/feature",
        json=body,
        headers={"X-CSRF-Token": token},
    )
    return res.status_code, res.json()


async def apply_certification(client, token: str, work_id: str) -> tuple[int, dict]:
    res = await client.post(
        "/api/member/certifications",
        json={"work_id": work_id},
        headers={"X-CSRF-Token": token},
    )
    return res.status_code, res.json()


# ---------------------------------------------------------------------------
# Certificate helpers
# ---------------------------------------------------------------------------
async def issue_certificate(
    client, token: str, request_id: str
) -> tuple[int, dict]:
    res = await client.post(
        "/api/admin/certificates",
        json={"request_id": request_id},
        headers={"X-CSRF-Token": token},
    )
    return res.status_code, res.json()


async def revoke_certificate(
    client, token: str, certificate_id: str, reason: str = "Issued in error"
) -> tuple[int, dict]:
    res = await client.post(
        f"/api/admin/certificates/{certificate_id}/revoke",
        json={"reason": reason},
        headers={"X-CSRF-Token": token},
    )
    return res.status_code, res.json()


async def email_certificate(
    client, token: str, certificate_id: str
) -> tuple[int, dict]:
    res = await client.post(
        f"/api/admin/certificates/{certificate_id}/email",
        headers={"X-CSRF-Token": token},
    )
    return res.status_code, res.json()


def capture_certificate_email(monkeypatch, *, fail: bool = False) -> dict:
    """Patch the certificates service email sender to capture deliveries (or
    simulate a delivery failure) with no network access."""
    captured: dict = {"messages": [], "failed": fail}

    async def _fake_send(*, to, subject, text, attachments=()):  # noqa: ANN001
        if captured["failed"]:
            from app.services.email import EmailDeliveryError

            raise EmailDeliveryError("simulated SMTP failure")
        captured["messages"].append(
            {
                "to": to,
                "subject": subject,
                "text": text,
                "attachments": attachments,
            }
        )

    monkeypatch.setattr(
        "app.modules.certificates.service.send_email", _fake_send
    )
    return captured


# ---------------------------------------------------------------------------
# Activity helpers (Phase 1: projects / programmes / hackathons)
# ---------------------------------------------------------------------------
def pdf_bytes(body: str = "Brief body") -> bytes:
    """A minimal, header-valid PDF (validation only checks the magic + size)."""
    return (
        b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n"
        + body.encode("utf-8")
        + b"\ntrailer\n<<>>\n%%EOF\n"
    )


async def create_activity(client, token: str, **overrides) -> dict:
    payload = {"title": "Atlas Programme", "activity_type": "programme"}
    payload.update(overrides)
    res = await client.post(
        "/api/admin/activities", json=payload, headers={"X-CSRF-Token": token}
    )
    assert res.status_code == 201, res.text
    return res.json()


async def patch_activity(client, token: str, activity_id: str, **fields) -> tuple[int, dict]:
    res = await client.patch(
        f"/api/admin/activities/{activity_id}",
        json=fields,
        headers={"X-CSRF-Token": token},
    )
    return res.status_code, res.json()


async def publish_activity(client, token: str, activity_id: str) -> dict:
    status, body = await patch_activity(client, token, activity_id, status="published")
    assert status == 200, body
    return body


async def upload_activity_brief(
    client,
    token: str,
    activity_id: str,
    data: bytes | None = None,
    filename: str = "brief.pdf",
) -> tuple[int, dict]:
    res = await client.post(
        f"/api/admin/activities/{activity_id}/brief",
        files={"file": (filename, data if data is not None else pdf_bytes(), "application/pdf")},
        headers={"X-CSRF-Token": token},
    )
    return res.status_code, res.json()


async def invite_to_activity(
    client,
    token: str,
    activity_id: str,
    invitations: list[dict],
    *,
    subject: str | None = None,
    message: str | None = None,
) -> tuple[int, dict]:
    payload: dict = {"invitations": invitations}
    if subject is not None:
        payload["subject"] = subject
    if message is not None:
        payload["message"] = message
    res = await client.post(
        f"/api/admin/activities/{activity_id}/invitations",
        json=payload,
        headers={"X-CSRF-Token": token},
    )
    return res.status_code, res.json()


async def list_activity_participants(client, token: str, activity_id: str, **params) -> dict:
    res = await client.get(
        f"/api/admin/activities/{activity_id}/participants",
        params=params,
        headers={"X-CSRF-Token": token},
    )
    assert res.status_code == 200, res.text
    return res.json()


async def update_participant(
    client, token: str, activity_id: str, participation_id: str, **fields
) -> tuple[int, dict]:
    res = await client.patch(
        f"/api/admin/activities/{activity_id}/participants/{participation_id}",
        json=fields,
        headers={"X-CSRF-Token": token},
    )
    return res.status_code, res.json()


async def register_activity(client, token: str, slug: str) -> tuple[int, dict]:
    res = await client.post(
        f"/api/member/activities/{slug}/register",
        headers={"X-CSRF-Token": token},
    )
    return res.status_code, res.json()


async def withdraw_activity(client, token: str, slug: str) -> tuple[int, dict]:
    res = await client.post(
        f"/api/member/activities/{slug}/withdraw",
        headers={"X-CSRF-Token": token},
    )
    return res.status_code, res.json()


def capture_activity_emails(monkeypatch, *, fail: bool = False) -> dict:
    """Patch the activities service email sender to capture invitation
    deliveries (or simulate a delivery failure) with no network access."""
    captured: dict = {"messages": [], "failed": fail}

    async def _fake_send(*, to, subject, text, attachments=()):  # noqa: ANN001
        if captured["failed"]:
            from app.services.email import EmailDeliveryError

            raise EmailDeliveryError("simulated SMTP failure")
        captured["messages"].append({"to": to, "subject": subject, "text": text})

    monkeypatch.setattr("app.modules.activities.service.send_email", _fake_send)
    return captured