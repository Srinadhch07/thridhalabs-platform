"""Certificate issuance / revocation / delivery / verification logic.

Guarantees enforced here:
  * Issuance is an explicit admin action, separate from review. Approving a
    request and issuing its certificate happen atomically from the caller's
    point of view: the request is flipped to `approved` first, then the PDF is
    generated + stored, then the record is written. Nothing is reported as
    issued until the record exists.
  * Duplicate issuance is impossible: a unique index on `request_id` backs an
    idempotent check, so a re-click or a concurrent race returns the same
    certificate instead of issuing a second one.
  * The certificate id is collision-resistant and unique (unique index, retry
    on duplicate key); it is never derived from the sequential Mongo id.
  * Revocation is a status change with a permanent audit trail — never a delete,
    never an id reuse.
  * The verification URL is built from a configured, non-localhost origin; QR
    codes always encode the full URL. If it is not configured, issuance fails
    loudly rather than printing a useless QR.
"""

from __future__ import annotations

from datetime import datetime, timezone
from urllib.parse import urlparse

from pymongo.errors import DuplicateKeyError

from app.core.config import get_settings
from app.core.errors import AppError
from app.core.logging import get_logger
from app.models.admin import Admin
from app.models.certificate import (
    CERTIFICATE_SCHEMA_VERSION,
    Certificate,
    CertificateEmailStatus,
    CertificateStatus,
    MAX_EMAIL_ERROR_LENGTH,
)
from app.models.certification import CertificationStatus
from app.models.member import Member
from app.models.work import MemberWork
from app.modules.branding import repository as branding_repository
from app.modules.certificates import pdf as pdf_render
from app.modules.certificates import repository
from app.modules.certifications import repository as certifications_repository
from app.modules.certifications import service as certifications_service
from app.modules.media import service as media_service
from app.modules.members import repository as members_repository
from app.modules.members import service as members_service
from app.modules.works import service as works_service
from app.services.email import EmailAttachment, EmailDeliveryError, send_email
from app.storage import get_storage_provider
from app.storage.base import StorageError, StorageObjectNotFoundError

log = get_logger("certificates")

CERTIFICATE_PDF_MIME = "application/pdf"

#: Request states from which a certificate may be issued (approve-on-issue).
_ISSUABLE_STATES = {
    CertificationStatus.SUBMITTED,
    CertificationStatus.UNDER_REVIEW,
    CertificationStatus.APPROVED,
}

_LOCAL_HOSTS = {"localhost", "127.0.0.1", "0.0.0.0", "::1", ""}


# ---------------------------------------------------------------------------
# Verification URL / public origin
# ---------------------------------------------------------------------------
def resolve_verification_base_url() -> str:
    """Return the canonical public origin for verification links, or raise.

    A QR code printed onto a PDF must resolve for a third party, so a missing
    or localhost-only configuration is a hard error, not a silent fallback.
    """
    base = get_settings().verification_base_url
    if not base:
        raise AppError(
            503,
            "CERTIFICATE_URL_NOT_CONFIGURED",
            "Certificate verification URL is not configured "
            "(set CERTIFICATE_VERIFY_BASE_URL or FRONTEND_URL)",
        )
    parsed = urlparse(base)
    host = (parsed.hostname or "").lower()
    if parsed.scheme not in ("http", "https") or not parsed.netloc:
        raise AppError(
            503,
            "CERTIFICATE_URL_NOT_CONFIGURED",
            "Certificate verification base URL must be an absolute http(s) URL",
        )
    if host in _LOCAL_HOSTS or host.endswith(".local"):
        raise AppError(
            503,
            "CERTIFICATE_URL_NOT_CONFIGURED",
            "Certificate verification base URL must not be a localhost address",
        )
    return base


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _now() -> datetime:
    return datetime.now(timezone.utc)


def _storage_key(certificate_id: str, issued_at: datetime) -> str:
    return f"certificates/{issued_at.year}/{issued_at.month:02d}/{certificate_id}.pdf"


def _pdf_filename(certificate_id: str) -> str:
    return f"Thridha-Labs-Certificate-{certificate_id}.pdf"


async def _brand_context() -> dict:
    """Best-effort brand name + logo for the certificate. Never fails issuance.

    The certificate uses its own fixed ivory-and-gold palette, so the runtime
    brand colours are intentionally not forwarded to the renderer; only the
    brand name (wordmark) and the existing uploaded logo are reused.
    """
    context: dict = {
        "brand_name": "Thridha Labs",
        "logo_png": None,
    }
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
            log.warning("Certificate logo unavailable (%s)", type(exc).__name__)
    return context


# ---------------------------------------------------------------------------
# Issuance
# ---------------------------------------------------------------------------
async def issue_certificate(
    admin: Admin, request_id: str, *, by_role: str
) -> Certificate:
    request = await certifications_repository.find_by_id(request_id)
    if request is None:
        raise AppError(404, "CERTIFICATION_NOT_FOUND", "Review request was not found")

    # Idempotency: one certificate per request, forever.
    existing = await repository.find_by_request_id(request_id)
    if existing is not None:
        return existing

    if request.status not in _ISSUABLE_STATES:
        raise AppError(
            409,
            "CERTIFICATION_NOT_APPROVED",
            "Only approved (or in-review) requests can be issued a certificate",
        )

    # Approve first when still in review; keep the review audit trail intact.
    if request.status in (
        CertificationStatus.SUBMITTED,
        CertificationStatus.UNDER_REVIEW,
    ):
        try:
            request = await certifications_service.decide(
                admin,
                request_id,
                action="approve",
                feedback=None,
                by_role=by_role,
            )
        except AppError as exc:
            if exc.code != "CERTIFICATION_ALREADY_DECIDED":
                raise
            # A concurrent approval won; re-read and continue only if approved.
            reloaded = await certifications_repository.find_by_id(request_id)
            if reloaded is None or reloaded.status != CertificationStatus.APPROVED:
                raise
            request = reloaded

    member = await members_repository.find_by_id(request.member_id)
    member_name = certifications_service.member_display_name(
        member, request.member_id
    )
    member_readable_id = member.member_id if member is not None else ""

    base_url = resolve_verification_base_url()
    issued_at = _now()
    certificate_id = pdf_render.generate_certificate_id(issued_at.year)
    verification_url = pdf_render.build_verification_url(base_url, certificate_id)
    qr_png = pdf_render.generate_qr_png(verification_url)
    brand = await _brand_context()
    pdf_bytes = pdf_render.render_certificate_pdf(
        certificate_id=certificate_id,
        member_name=member_name,
        work_title=request.snapshot.title,
        issued_at=issued_at,
        verification_url=verification_url,
        qr_png=qr_png,
        **brand,
    )

    provider = get_storage_provider()
    object_key = _storage_key(certificate_id, issued_at)
    pdf_filename = _pdf_filename(certificate_id)
    try:
        await provider.put(object_key, pdf_bytes, content_type=CERTIFICATE_PDF_MIME)
    except StorageError as exc:
        log.error("Certificate PDF store failed (%s)", type(exc).__name__)
        raise AppError(
            500, "STORAGE_ERROR", "Could not store the certificate PDF"
        ) from exc

    try:
        certificate = await repository.insert_certificate(
            certificate_id=certificate_id,
            request_id=request_id,
            work_id=request.work_id,
            member_id=request.member_id,
            member_readable_id=member_readable_id,
            member_name=member_name,
            work_title=request.snapshot.title,
            work_slug=request.snapshot.slug,
            decided_at=request.decided_at,
            issued_at=issued_at,
            issued_by=admin.id,
            issued_by_role=by_role,
            template_version=CERTIFICATE_SCHEMA_VERSION,
            pdf_object_key=object_key,
            pdf_filename=pdf_filename,
            pdf_size_bytes=len(pdf_bytes),
            pdf_sha256=pdf_render.sha256_hex(pdf_bytes),
            qr_verify_url=verification_url,
        )
    except DuplicateKeyError:
        # Lost an id race: prefer the request_id winner, else retry with a new id
        # a couple of times (certificate_id collision is astronomically rare).
        await _safe_delete(provider, object_key)
        winner = await repository.find_by_request_id(request_id)
        if winner is not None:
            return winner
        raise AppError(
            409,
            "CERTIFICATE_EXISTS",
            "A certificate already exists for this request",
        )

    log.info(
        "Certificate issued id=%s request_id=%s by admin=%s",
        certificate_id,
        request_id,
        admin.id,
    )
    return certificate


async def _safe_delete(provider, key: str) -> None:
    try:
        await provider.delete(key)
    except StorageError as exc:  # pragma: no cover - best-effort cleanup
        log.warning("Orphan certificate object cleanup failed (%s)", type(exc).__name__)


# ---------------------------------------------------------------------------
# Revocation
# ---------------------------------------------------------------------------
async def revoke_certificate(
    admin: Admin, certificate_id: str, reason: str, *, by_role: str
) -> Certificate:
    certificate = await admin_get(certificate_id)
    if certificate.status == CertificateStatus.REVOKED:
        raise AppError(
            409, "CERTIFICATE_ALREADY_REVOKED", "This certificate is already revoked"
        )
    updated = await repository.update_certificate(
        certificate_id,
        {
            "status": CertificateStatus.REVOKED.value,
            "revoked_at": _now(),
            "revoked_by": admin.id,
            "revocation_reason": reason,
        },
    )
    if updated is None:  # pragma: no cover - deleted concurrently
        raise AppError(404, "CERTIFICATE_NOT_FOUND", "Certificate was not found")
    log.info(
        "Certificate revoked id=%s by admin=%s role=%s",
        certificate_id,
        admin.id,
        by_role,
    )
    return updated


# ---------------------------------------------------------------------------
# Delivery
# ---------------------------------------------------------------------------
def _email_body(certificate: Certificate) -> str:
    lines = [
        f"Hello {certificate.member_name},",
        "",
        "Congratulations — Thridha Labs has issued a certificate recognizing "
        f"your work \"{certificate.work_title}\".",
        "",
        f"Certificate ID: {certificate.certificate_id}",
        f"Verify at: {certificate.qr_verify_url}",
    ]
    if certificate.status == CertificateStatus.REVOKED:
        lines.append("")
        lines.append("Note: this certificate has since been revoked.")
    lines.append("")
    lines.append("A PDF copy is attached.")
    lines.append("")
    lines.append("— Thridha Labs")
    return "\n".join(lines)


async def send_certificate_email(admin: Admin, certificate_id: str) -> Certificate:
    certificate = await admin_get(certificate_id)
    member = await members_repository.find_by_id(certificate.member_id)
    if member is None:
        raise AppError(
            409,
            "CERTIFICATE_MEMBER_MISSING",
            "The certificate's member no longer exists; cannot deliver by email",
        )

    attempts = certificate.email_attempts + 1
    try:
        pdf_bytes, _ = await open_pdf(certificate)
        await send_email(
            to=member.email,
            subject=f"Your Thridha Labs certificate ({certificate.certificate_id})",
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
                "email_status": CertificateEmailStatus.FAILED.value,
                "email_attempts": attempts,
                "email_last_error": error,
            },
        )
        log.warning(
            "Certificate email failed id=%s by admin=%s", certificate_id, admin.id
        )
        raise AppError(
            502,
            "CERTIFICATE_EMAIL_FAILED",
            "The certificate email could not be delivered; the certificate "
            "remains valid and downloadable",
        ) from exc

    sent_at = _now()
    updated = await repository.update_certificate(
        certificate_id,
        {
            "email_status": CertificateEmailStatus.SENT.value,
            "email_sent_at": sent_at,
            "email_attempts": attempts,
            "email_last_error": None,
        },
    )
    if updated is None:  # pragma: no cover - deleted concurrently
        raise AppError(404, "CERTIFICATE_NOT_FOUND", "Certificate was not found")
    log.info(
        "Certificate emailed id=%s to member=%s by admin=%s",
        certificate_id,
        member.member_id,
        admin.id,
    )
    return updated


# ---------------------------------------------------------------------------
# Reads
# ---------------------------------------------------------------------------
async def admin_get(certificate_id: str) -> Certificate:
    certificate = await repository.find_by_public_id(certificate_id)
    if certificate is None:
        raise AppError(404, "CERTIFICATE_NOT_FOUND", "Certificate was not found")
    return certificate


def _validate_status_filter(status: str | None) -> str | None:
    if status is None:
        return None
    if status not in {item.value for item in CertificateStatus}:
        raise AppError(422, "INVALID_STATUS", "Unknown certificate status filter")
    return status


async def admin_list(
    *,
    page: int,
    page_size: int,
    status: str | None,
    member_id: str | None,
    request_id: str | None,
) -> tuple[list[Certificate], int]:
    query: dict = {}
    status = _validate_status_filter(status)
    if status:
        query["status"] = status
    if member_id:
        query["member_id"] = member_id
    if request_id:
        query["request_id"] = request_id
    return await repository.list_certificates(
        query=query, skip=(page - 1) * page_size, limit=page_size
    )


async def list_for_member(
    member: Member, *, page: int, page_size: int, status: str | None
) -> tuple[list[Certificate], int]:
    query: dict = {"member_id": member.id}
    status = _validate_status_filter(status)
    if status:
        query["status"] = status
    return await repository.list_certificates(
        query=query, skip=(page - 1) * page_size, limit=page_size
    )


async def get_for_member(member: Member, certificate_id: str) -> Certificate:
    certificate = await repository.find_by_public_id(certificate_id)
    if certificate is None or certificate.member_id != member.id:
        raise AppError(404, "CERTIFICATE_NOT_FOUND", "Certificate was not found")
    return certificate


async def get_by_request(request_id: str) -> Certificate | None:
    return await repository.find_by_request_id(request_id)


async def open_pdf(certificate: Certificate) -> tuple[bytes, str]:
    provider = get_storage_provider()
    try:
        data = await provider.get(certificate.pdf_object_key)
    except StorageObjectNotFoundError as exc:
        raise AppError(
            404, "CERTIFICATE_PDF_NOT_FOUND", "The certificate PDF is unavailable"
        ) from exc
    except StorageError as exc:
        log.error(
            "Certificate PDF read failed id=%s (%s)",
            certificate.certificate_id,
            type(exc).__name__,
        )
        raise AppError(
            500, "STORAGE_ERROR", "Could not read the certificate PDF"
        ) from exc
    return data, certificate.pdf_filename


# ---------------------------------------------------------------------------
# Public verification
# ---------------------------------------------------------------------------
async def _public_work_presentation(
    certificate: Certificate, owner: Member, live_work: MemberWork, base: str
) -> dict | None:
    """Build the certified-work projection from the approved snapshot.

    Returns None (verification still succeeds) when the request/snapshot is
    missing — legacy certificates or unexpectedly deleted review data. The
    snapshot is the immutable, reviewed version; `live_work` only supplies the
    "current version" link and a freshness flag.
    """
    request = await certifications_repository.find_by_id(certificate.request_id)
    if request is None:
        return None
    snapshot = request.snapshot
    return {
        "title": snapshot.title,
        "summary": snapshot.summary,
        "cover_media_id": snapshot.cover_media_id,
        "tags": snapshot.tags,
        "external_links": snapshot.external_links,
        "content": snapshot.content,
        "author": {
            "member_id": owner.member_id,
            "display_name": owner.profile.display_name
            or owner.full_name
            or owner.member_id,
            "picture_media_id": owner.profile.picture_media_id,
        },
        "member_profile_url": f"{base}/members/{owner.member_id}",
        "certified_at": request.decided_at or certificate.issued_at,
        "current_work_url": f"{base}/members/{owner.member_id}/works/{live_work.slug}",
        "has_newer_version": live_work.version != request.snapshot_version,
    }


async def get_public(certificate_id: str) -> dict:
    certificate = await repository.find_by_public_id(certificate_id)
    if certificate is None:
        raise AppError(404, "CERTIFICATE_NOT_FOUND", "Certificate was not found")

    work_url: str | None = None
    work_presentation: dict | None = None
    base = get_settings().verification_base_url
    if base and certificate.member_readable_id:
        try:
            owner = await members_service.get_public_member(
                certificate.member_readable_id
            )
            # Resolve by stable id so a slug rename does not orphan the link, and
            # so the work is only surfaced while still published + public-visible.
            live_work = await works_service.get_public_work_by_id(
                owner, certificate.work_id
            )
        except AppError:
            # Member/work no longer public — verification of the credential still
            # works, the work section is simply omitted (never leaks private data).
            work_url = None
            work_presentation = None
        else:
            work_url = f"{base}/members/{owner.member_id}/works/{live_work.slug}"
            work_presentation = await _public_work_presentation(
                certificate, owner, live_work, base
            )

    return {
        "certificate_id": certificate.certificate_id,
        "status": certificate.status,
        "issued_at": certificate.issued_at,
        "member_name": certificate.member_name,
        "work_title": certificate.work_title,
        "work_url": work_url,
        "work": work_presentation,
        "revoked_at": certificate.revoked_at,
        "revocation_reason": (
            certificate.revocation_reason
            if certificate.status == CertificateStatus.REVOKED
            else None
        ),
    }
