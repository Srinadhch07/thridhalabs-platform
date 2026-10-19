"""Activity-certificate business logic: eligibility, issuance, bulk, delivery,
revocation and public verification.

Guarantees mirror the Work Recognition certificate service but operate entirely
within this subsystem's own collections:

  * Issuance always validates eligibility **server-side** against
    `activity_participations`; the client never asserts who participated.
  * At most one certificate per `(activity, member, award)` — an idempotent
    pre-check plus a unique index make duplicate/concurrent issuance safe, while
    genuinely distinct awards remain allowed.
  * The activity, recipient, award and optional recognized work are snapshotted.
  * Revocation is a status change with a permanent audit trail; ids are never
    reused and records are never deleted.
  * The verification URL is built from a configured, non-localhost origin; QR
    codes always encode the full `/verify-activity-certificate/<id>` URL.
  * No read or write ever touches the Work Recognition `certificates`
    collection.
"""

from __future__ import annotations

from datetime import datetime, timezone
from urllib.parse import urlparse

from pymongo.errors import DuplicateKeyError

from app.core.config import get_settings
from app.core.errors import AppError
from app.core.logging import get_logger
from app.models.activity import Activity, ActivityParticipation, ParticipationStatus
from app.models.activity_certificate import (
    ACTIVITY_CERTIFICATE_SCHEMA_VERSION,
    MAX_EMAIL_ERROR_LENGTH,
    ActivityAwardCategory,
    ActivityCertificate,
    ActivityCertificateAuditAction,
    ActivityCertificateEmailStatus,
    ActivityCertificateStatus,
    ActivityCertificateTemplate,
    normalize_award_key,
)
from app.models.admin import Admin
from app.models.member import Member
from app.models.work import MemberWork
from app.modules.activities import repository as activities_repository
from app.modules.activity_certificates import pdf as pdf_render
from app.modules.activity_certificates import repository
from app.modules.branding import repository as branding_repository
from app.modules.certificates.pdf import generate_qr_png, sha256_hex
from app.modules.media import service as media_service
from app.modules.members import repository as members_repository
from app.modules.members import service as members_service
from app.modules.works import repository as works_repository
from app.modules.works import service as works_service
from app.services.email import EmailAttachment, EmailDeliveryError, send_email
from app.storage import get_storage_provider
from app.storage.base import StorageError, StorageObjectNotFoundError

log = get_logger("activity_certificates")

CERTIFICATE_PDF_MIME = "application/pdf"

_LOCAL_HOSTS = {"localhost", "127.0.0.1", "0.0.0.0", "::1", ""}

_TEMPLATE_AUDIT_KEY = "__template__"


# ---------------------------------------------------------------------------
# Verification URL / public origin
# ---------------------------------------------------------------------------
def resolve_verification_base_url() -> str:
    base = get_settings().verification_base_url
    if not base:
        raise AppError(
            503,
            "ACTIVITY_CERTIFICATE_URL_NOT_CONFIGURED",
            "Activity certificate verification URL is not configured "
            "(set CERTIFICATE_VERIFY_BASE_URL or FRONTEND_URL)",
        )
    parsed = urlparse(base)
    host = (parsed.hostname or "").lower()
    if parsed.scheme not in ("http", "https") or not parsed.netloc:
        raise AppError(
            503,
            "ACTIVITY_CERTIFICATE_URL_NOT_CONFIGURED",
            "Activity certificate verification base URL must be an absolute http(s) URL",
        )
    if host in _LOCAL_HOSTS or host.endswith(".local"):
        raise AppError(
            503,
            "ACTIVITY_CERTIFICATE_URL_NOT_CONFIGURED",
            "Activity certificate verification base URL must not be a localhost address",
        )
    return base


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _now() -> datetime:
    return datetime.now(timezone.utc)


def _storage_key(certificate_id: str, issued_at: datetime) -> str:
    return f"activity-certificates/{issued_at.year}/{certificate_id}.pdf"


def _pdf_filename(certificate_id: str) -> str:
    return f"ThridhaLabs-Activity-Certificate-{certificate_id}.pdf"


async def _brand_context() -> dict:
    context: dict = {"brand_name": "Thridha Labs", "logo_png": None}
    branding = await branding_repository.get()
    if branding is None:
        return context
    context["brand_name"] = get_settings().APP_NAME
    logo_id = branding.media.logo
    if logo_id:
        try:
            logo_bytes, _ = await media_service.get_media_file(logo_id, "original")
            context["logo_png"] = logo_bytes
        except (AppError, StorageError) as exc:
            log.warning("Activity certificate logo unavailable (%s)", type(exc).__name__)
    return context


async def get_or_default_template() -> ActivityCertificateTemplate:
    template = await repository.get_template()
    return template or ActivityCertificateTemplate()


async def update_template(admin: Admin, payload) -> ActivityCertificateTemplate:
    template = payload.to_template()
    saved = await repository.save_template(template, updated_by=admin.id)
    await repository.append_audit(
        certificate_id=_TEMPLATE_AUDIT_KEY,
        action=ActivityCertificateAuditAction.TEMPLATE_UPDATED,
        actor_id=admin.id,
        actor_role=admin.role.value,
        detail="Activity certificate template updated",
    )
    return saved


def _resolve_award(
    template: ActivityCertificateTemplate,
    category: ActivityAwardCategory,
    custom_label: str | None,
    custom_statement: str | None,
) -> tuple[str, str, str]:
    value = category.value
    if category == ActivityAwardCategory.CUSTOM:
        label = (custom_label or "").strip()
        if not label:
            raise AppError(
                422,
                "AWARD_LABEL_REQUIRED",
                "A custom award must include a custom_award_label",
            )
        statement = (custom_statement or "").strip()
    else:
        label = template.label_for(value, None)
        statement = template.statement_for(value, None)
    return label, statement, normalize_award_key(value, label if category == ActivityAwardCategory.CUSTOM else None)


async def _resolve_activity(activity_id: str) -> Activity:
    activity = await activities_repository.find_activity_by_id(activity_id)
    if activity is None:
        raise AppError(404, "ACTIVITY_NOT_FOUND", "Activity was not found")
    return activity


async def _require_confirmed_participant(
    activity_id: str, member_id: str
) -> ActivityParticipation:
    participation = await activities_repository.find_participation(activity_id, member_id)
    if participation is None or participation.status != ParticipationStatus.CONFIRMED:
        raise AppError(
            409,
            "PARTICIPANT_NOT_ELIGIBLE",
            "Only confirmed participants of this activity can be issued a certificate",
        )
    return participation


async def _resolve_work(member: Member, work_id: str | None) -> MemberWork | None:
    if not work_id:
        return None
    work = await works_repository.find_by_id(work_id)
    if work is None or work.member_id != member.id:
        raise AppError(
            404,
            "WORK_NOT_FOUND",
            "The associated work was not found for this member",
        )
    return work


def member_display_name(member: Member) -> str:
    return member.profile.display_name or member.full_name or member.member_id


# ---------------------------------------------------------------------------
# Issuance
# ---------------------------------------------------------------------------
async def _issue_one(
    admin: Admin,
    *,
    activity: Activity,
    member: Member,
    category: ActivityAwardCategory,
    custom_label: str | None,
    custom_statement: str | None,
    work: MemberWork | None,
    template: ActivityCertificateTemplate,
    base_url: str,
    by_role: str,
) -> tuple[ActivityCertificate, bool]:
    label, statement, award_key = _resolve_award(
        template, category, custom_label, custom_statement
    )

    existing = await repository.find_by_award(activity.id, member.id, award_key)
    if existing is not None:
        return existing, False

    issued_at = _now()
    certificate_id = pdf_render.generate_activity_certificate_id(issued_at.year)
    verification_url = pdf_render.build_activity_verification_url(base_url, certificate_id)
    qr_png = generate_qr_png(verification_url)
    brand = await _brand_context()
    snapshot = template.snapshot()
    pdf_bytes = pdf_render.render_activity_certificate_pdf(
        certificate_id=certificate_id,
        member_name=member_display_name(member),
        activity_title=activity.title,
        activity_type=activity.activity_type.value,
        award_label=label,
        award_statement=statement,
        work_title=work.title if work is not None else None,
        issued_at=issued_at,
        verification_url=verification_url,
        qr_png=qr_png,
        template=snapshot,
        **brand,
    )

    provider = get_storage_provider()
    object_key = _storage_key(certificate_id, issued_at)
    pdf_filename = _pdf_filename(certificate_id)
    try:
        await provider.put(object_key, pdf_bytes, content_type=CERTIFICATE_PDF_MIME)
    except StorageError as exc:
        log.error("Activity certificate PDF store failed (%s)", type(exc).__name__)
        raise AppError(
            500, "STORAGE_ERROR", "Could not store the activity certificate PDF"
        ) from exc

    try:
        certificate = await repository.insert_certificate(
            certificate_id=certificate_id,
            activity_id=activity.id,
            activity_title=activity.title,
            activity_slug=activity.slug,
            activity_type=activity.activity_type.value,
            award_category=category.value,
            award_label=label,
            award_statement=statement,
            award_key=award_key,
            member_id=member.id,
            member_readable_id=member.member_id,
            member_name=member_display_name(member),
            work_id=work.id if work is not None else None,
            work_title=work.title if work is not None else None,
            work_slug=work.slug if work is not None else None,
            template_version=ACTIVITY_CERTIFICATE_SCHEMA_VERSION,
            template_snapshot=snapshot,
            issued_at=issued_at,
            issued_by=admin.id,
            issued_by_role=by_role,
            pdf_object_key=object_key,
            pdf_filename=pdf_filename,
            pdf_size_bytes=len(pdf_bytes),
            pdf_sha256=sha256_hex(pdf_bytes),
            qr_verify_url=verification_url,
        )
    except DuplicateKeyError:
        await _safe_delete(provider, object_key)
        winner = await repository.find_by_award(activity.id, member.id, award_key)
        if winner is not None:
            return winner, False
        raise AppError(
            409,
            "ACTIVITY_CERTIFICATE_EXISTS",
            "A certificate already exists for this award",
        )

    await repository.append_audit(
        certificate_id=certificate_id,
        action=ActivityCertificateAuditAction.ISSUED,
        actor_id=admin.id,
        actor_role=by_role,
        detail=f"Award: {label}",
    )
    log.info(
        "Activity certificate issued id=%s activity=%s member=%s by admin=%s",
        certificate_id,
        activity.id,
        member.member_id,
        admin.id,
    )
    return certificate, True


async def _safe_delete(provider, key: str) -> None:
    try:
        await provider.delete(key)
    except StorageError as exc:  # pragma: no cover - best-effort cleanup
        log.warning("Orphan activity certificate cleanup failed (%s)", type(exc).__name__)


async def issue_certificate(admin: Admin, payload, *, by_role: str) -> ActivityCertificate:
    activity = await _resolve_activity(payload.activity_id)
    member = await members_repository.find_by_id(payload.member_id)
    if member is None:
        raise AppError(404, "MEMBER_NOT_FOUND", "Member was not found")
    await _require_confirmed_participant(activity.id, member.id)
    work = await _resolve_work(member, payload.work_id)
    template = await get_or_default_template()
    base_url = resolve_verification_base_url()
    certificate, _ = await _issue_one(
        admin,
        activity=activity,
        member=member,
        category=payload.award_category,
        custom_label=payload.custom_award_label,
        custom_statement=payload.custom_statement,
        work=work,
        template=template,
        base_url=base_url,
        by_role=by_role,
    )
    return certificate


async def issue_bulk(admin: Admin, payload, *, by_role: str) -> dict:
    activity = await _resolve_activity(payload.activity_id)
    template = await get_or_default_template()
    base_url = resolve_verification_base_url()

    recipients = payload.recipients
    member_ids = [r.member_id for r in recipients]
    members = await members_repository.find_many_by_ids(member_ids)

    issued: list[ActivityCertificate] = []
    skipped: list[dict] = []
    failed: list[dict] = []

    for recipient in recipients:
        member = members.get(recipient.member_id)
        if member is None:
            failed.append({"member_id": recipient.member_id, "reason": "Member was not found"})
            continue
        participation = await activities_repository.find_participation(
            activity.id, member.id
        )
        if participation is None or participation.status != ParticipationStatus.CONFIRMED:
            failed.append(
                {
                    "member_id": recipient.member_id,
                    "reason": "Not a confirmed participant of this activity",
                }
            )
            continue
        category = recipient.award_category or payload.award_category
        try:
            work = await _resolve_work(member, recipient.work_id)
            certificate, created = await _issue_one(
                admin,
                activity=activity,
                member=member,
                category=category,
                custom_label=recipient.custom_award_label,
                custom_statement=recipient.custom_statement,
                work=work,
                template=template,
                base_url=base_url,
                by_role=by_role,
            )
        except AppError as exc:
            failed.append({"member_id": recipient.member_id, "reason": exc.message})
            continue
        if created:
            issued.append(certificate)
        else:
            skipped.append(
                {
                    "member_id": recipient.member_id,
                    "certificate_id": certificate.certificate_id,
                    "reason": "Already issued for this award",
                }
            )

    return {
        "issued": issued,
        "skipped": skipped,
        "failed": failed,
        "issued_count": len(issued),
        "skipped_count": len(skipped),
        "failed_count": len(failed),
    }


# ---------------------------------------------------------------------------
# Revocation
# ---------------------------------------------------------------------------
async def revoke_certificate(
    admin: Admin, certificate_id: str, reason: str, *, by_role: str
) -> ActivityCertificate:
    certificate = await admin_get(certificate_id)
    if certificate.status == ActivityCertificateStatus.REVOKED:
        raise AppError(
            409,
            "ACTIVITY_CERTIFICATE_ALREADY_REVOKED",
            "This activity certificate is already revoked",
        )
    updated = await repository.update_certificate(
        certificate_id,
        {
            "status": ActivityCertificateStatus.REVOKED.value,
            "revoked_at": _now(),
            "revoked_by": admin.id,
            "revocation_reason": reason,
        },
    )
    if updated is None:  # pragma: no cover - deleted concurrently
        raise AppError(404, "ACTIVITY_CERTIFICATE_NOT_FOUND", "Certificate was not found")
    await repository.append_audit(
        certificate_id=certificate_id,
        action=ActivityCertificateAuditAction.REVOKED,
        actor_id=admin.id,
        actor_role=by_role,
        detail=reason,
    )
    log.info(
        "Activity certificate revoked id=%s by admin=%s role=%s",
        certificate_id,
        admin.id,
        by_role,
    )
    return updated


# ---------------------------------------------------------------------------
# Delivery
# ---------------------------------------------------------------------------
def _email_body(certificate: ActivityCertificate) -> str:
    lines = [
        f"Hello {certificate.member_name},",
        "",
        "Thridha Labs has issued an activity certificate recognising your "
        f"{certificate.award_label} in \"{certificate.activity_title}\".",
        "",
        f"Certificate ID: {certificate.certificate_id}",
        f"Verify at: {certificate.qr_verify_url}",
    ]
    if certificate.status == ActivityCertificateStatus.REVOKED:
        lines.append("")
        lines.append("Note: this certificate has since been revoked.")
    lines.append("")
    lines.append("A PDF copy is attached.")
    lines.append("")
    lines.append("- Thridha Labs")
    return "\n".join(lines)


async def send_certificate_email(admin: Admin, certificate_id: str) -> ActivityCertificate:
    certificate = await admin_get(certificate_id)
    member = await members_repository.find_by_id(certificate.member_id)
    if member is None:
        raise AppError(
            409,
            "ACTIVITY_CERTIFICATE_MEMBER_MISSING",
            "The certificate's member no longer exists; cannot deliver by email",
        )

    attempts = certificate.email_attempts + 1
    try:
        pdf_bytes, _ = await open_pdf(certificate)
        await send_email(
            to=member.email,
            subject=f"Your Thridha Labs activity certificate ({certificate.certificate_id})",
            text=_email_body(certificate),
            attachments=(
                EmailAttachment(
                    filename=certificate.pdf_filename,
                    content=pdf_bytes,
                    mime_type=CERTIFICATE_PDF_MIME,
                ),
            ),
        )
    except (EmailDeliveryError, AppError) as exc:
        error = str(exc)[:MAX_EMAIL_ERROR_LENGTH]
        await repository.update_certificate(
            certificate_id,
            {
                "email_status": ActivityCertificateEmailStatus.FAILED.value,
                "email_attempts": attempts,
                "email_last_error": error,
            },
        )
        await repository.append_audit(
            certificate_id=certificate_id,
            action=ActivityCertificateAuditAction.EMAIL_FAILED,
            actor_id=admin.id,
            actor_role=admin.role.value,
            detail=error,
        )
        raise AppError(
            502,
            "ACTIVITY_CERTIFICATE_EMAIL_FAILED",
            "The certificate email could not be delivered; the certificate "
            "remains valid and downloadable",
        ) from exc

    sent_at = _now()
    updated = await repository.update_certificate(
        certificate_id,
        {
            "email_status": ActivityCertificateEmailStatus.SENT.value,
            "email_sent_at": sent_at,
            "email_attempts": attempts,
            "email_last_error": None,
        },
    )
    if updated is None:  # pragma: no cover - deleted concurrently
        raise AppError(404, "ACTIVITY_CERTIFICATE_NOT_FOUND", "Certificate was not found")
    await repository.append_audit(
        certificate_id=certificate_id,
        action=ActivityCertificateAuditAction.EMAIL_SENT,
        actor_id=admin.id,
        actor_role=admin.role.value,
        detail=f"Sent to {member.member_id}",
    )
    return updated


# ---------------------------------------------------------------------------
# Reads
# ---------------------------------------------------------------------------
async def admin_get(certificate_id: str) -> ActivityCertificate:
    certificate = await repository.find_by_public_id(certificate_id)
    if certificate is None:
        raise AppError(
            404, "ACTIVITY_CERTIFICATE_NOT_FOUND", "Activity certificate was not found"
        )
    return certificate


def _validate_status_filter(status: str | None) -> str | None:
    if status is None:
        return None
    if status not in {item.value for item in ActivityCertificateStatus}:
        raise AppError(422, "INVALID_STATUS", "Unknown activity certificate status filter")
    return status


async def admin_list(
    *,
    page: int,
    page_size: int,
    status: str | None,
    activity_id: str | None,
    member_id: str | None,
    award_category: str | None,
) -> tuple[list[ActivityCertificate], int]:
    query: dict = {}
    status_value = _validate_status_filter(status)
    if status_value:
        query["status"] = status_value
    if activity_id:
        query["activity_id"] = activity_id
    if member_id:
        query["member_id"] = member_id
    if award_category:
        if award_category not in {item.value for item in ActivityAwardCategory}:
            raise AppError(422, "INVALID_AWARD_CATEGORY", "Unknown award category filter")
        query["award_category"] = award_category
    return await repository.list_certificates(
        query=query, skip=(page - 1) * page_size, limit=page_size
    )


async def list_for_member(
    member: Member, *, page: int, page_size: int, status: str | None
) -> tuple[list[ActivityCertificate], int]:
    query: dict = {"member_id": member.id}
    status_value = _validate_status_filter(status)
    if status_value:
        query["status"] = status_value
    return await repository.list_certificates(
        query=query, skip=(page - 1) * page_size, limit=page_size
    )


async def get_for_member(member: Member, certificate_id: str) -> ActivityCertificate:
    certificate = await repository.find_by_public_id(certificate_id)
    if certificate is None or certificate.member_id != member.id:
        raise AppError(
            404, "ACTIVITY_CERTIFICATE_NOT_FOUND", "Activity certificate was not found"
        )
    return certificate


async def open_pdf(certificate: ActivityCertificate) -> tuple[bytes, str]:
    provider = get_storage_provider()
    try:
        data = await provider.get(certificate.pdf_object_key)
    except StorageObjectNotFoundError as exc:
        raise AppError(
            404,
            "ACTIVITY_CERTIFICATE_PDF_NOT_FOUND",
            "The activity certificate PDF is unavailable",
        ) from exc
    except StorageError as exc:
        log.error(
            "Activity certificate PDF read failed id=%s (%s)",
            certificate.certificate_id,
            type(exc).__name__,
        )
        raise AppError(
            500, "STORAGE_ERROR", "Could not read the activity certificate PDF"
        ) from exc
    return data, certificate.pdf_filename


async def list_audit(certificate_id: str):
    return await repository.list_audit(certificate_id)


async def list_eligible_participants(activity_id: str) -> dict:
    activity = await _resolve_activity(activity_id)
    participations, _ = await activities_repository.list_participations(
        query={"activity_id": activity.id, "status": ParticipationStatus.CONFIRMED.value},
        sort=[("created_at", 1)],
        skip=0,
        limit=1000,
    )
    member_ids = [p.member_id for p in participations]
    members = await members_repository.find_many_by_ids(member_ids)
    issued = await repository.list_issued_keys(activity.id, member_ids)

    items = []
    for participation in participations:
        member = members.get(participation.member_id)
        if member is None:
            continue
        items.append(
            {
                "member_id": member.id,
                "member_readable_id": member.member_id,
                "member_name": member_display_name(member),
                "member_email": member.email,
                "participation_status": participation.status.value,
                "role": participation.role,
                "already_issued_awards": sorted(
                    key for (mid, key) in issued if mid == member.id
                ),
            }
        )
    return {"activity_id": activity.id, "activity_title": activity.title, "items": items}


# ---------------------------------------------------------------------------
# Public verification
# ---------------------------------------------------------------------------
async def _public_work(
    certificate: ActivityCertificate, base: str
) -> dict | None:
    if not certificate.work_id or not certificate.member_readable_id:
        return None
    try:
        owner = await members_service.get_public_member(certificate.member_readable_id)
        live_work = await works_service.get_public_work_by_id(owner, certificate.work_id)
    except AppError:
        return None
    return {
        "title": live_work.title,
        "url": f"{base}/members/{owner.member_id}/works/{live_work.slug}",
    }


async def get_public(certificate_id: str) -> dict:
    certificate = await repository.find_by_public_id(certificate_id)
    if certificate is None:
        raise AppError(
            404, "ACTIVITY_CERTIFICATE_NOT_FOUND", "Activity certificate was not found"
        )

    work: dict | None = None
    base = get_settings().verification_base_url
    if base:
        work = await _public_work(certificate, base)

    return {
        "certificate_id": certificate.certificate_id,
        "status": certificate.status,
        "issued_at": certificate.issued_at,
        "member_name": certificate.member_name,
        "activity_title": certificate.activity_title,
        "activity_type": certificate.activity_type,
        "award_category": certificate.award_category,
        "award_label": certificate.award_label,
        "award_statement": certificate.award_statement,
        "work": work,
        "revoked_at": certificate.revoked_at,
        "revocation_reason": (
            certificate.revocation_reason
            if certificate.status == ActivityCertificateStatus.REVOKED
            else None
        ),
    }
