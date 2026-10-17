"""Pydantic schemas for the certificate API (member, admin, public surfaces).

Response schemas never expose the private storage object key, Mongo `_id`, or
internal reviewer notes. The public verification response is a hand-picked
projection built by the service.
"""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.certificate import (
    MAX_REVOCATION_REASON_LENGTH,
    Certificate,
    CertificateEmailStatus,
    CertificateStatus,
)
from app.models.work import ContentDocument, ExternalLink
from app.modules.works.schemas import WorkPublicAuthor


class CertificateIssueRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    request_id: str = Field(min_length=1, max_length=64)


class CertificateRevokeRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    reason: str = Field(min_length=1, max_length=MAX_REVOCATION_REASON_LENGTH)

    def clean_reason(self) -> str:
        return self.reason.strip()


def _download_path(certificate: Certificate, *, scope: str) -> str:
    return f"/{scope}/certificates/{certificate.certificate_id}/download"


class CertificateMemberResponse(BaseModel):
    """Member-safe view of a certificate they own."""

    model_config = ConfigDict(extra="forbid")

    certificate_id: str
    request_id: str
    work_title: str
    work_slug: str
    member_name: str
    status: CertificateStatus
    issued_at: datetime
    revoked_at: datetime | None
    revocation_reason: str | None
    email_status: CertificateEmailStatus
    email_sent_at: datetime | None
    pdf_filename: str
    pdf_size_bytes: int
    verify_url: str
    download_path: str

    @classmethod
    def from_certificate(cls, certificate: Certificate) -> "CertificateMemberResponse":
        return cls(
            certificate_id=certificate.certificate_id,
            request_id=certificate.request_id,
            work_title=certificate.work_title,
            work_slug=certificate.work_slug,
            member_name=certificate.member_name,
            status=certificate.status,
            issued_at=certificate.issued_at,
            revoked_at=certificate.revoked_at,
            revocation_reason=certificate.revocation_reason if certificate.status == CertificateStatus.REVOKED else None,
            email_status=certificate.email_status,
            email_sent_at=certificate.email_sent_at,
            pdf_filename=certificate.pdf_filename,
            pdf_size_bytes=certificate.pdf_size_bytes,
            verify_url=certificate.qr_verify_url,
            download_path=_download_path(certificate, scope="member"),
        )


class CertificateAdminResponse(CertificateMemberResponse):
    """Admin view adds audit/issuance metadata (email attempts/errors)."""

    issued_by: str
    issued_by_role: str
    decided_at: datetime | None
    template_version: str
    email_attempts: int
    email_last_error: str | None

    @classmethod
    def from_certificate(cls, certificate: Certificate) -> "CertificateAdminResponse":
        return cls(
            certificate_id=certificate.certificate_id,
            request_id=certificate.request_id,
            work_title=certificate.work_title,
            work_slug=certificate.work_slug,
            member_name=certificate.member_name,
            status=certificate.status,
            issued_at=certificate.issued_at,
            revoked_at=certificate.revoked_at,
            revocation_reason=certificate.revocation_reason,
            email_status=certificate.email_status,
            email_sent_at=certificate.email_sent_at,
            pdf_filename=certificate.pdf_filename,
            pdf_size_bytes=certificate.pdf_size_bytes,
            verify_url=certificate.qr_verify_url,
            download_path=_download_path(certificate, scope="admin"),
            issued_by=certificate.issued_by,
            issued_by_role=certificate.issued_by_role,
            decided_at=certificate.decided_at,
            template_version=certificate.template_version,
            email_attempts=certificate.email_attempts,
            email_last_error=certificate.email_last_error,
        )


class CertificateListResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    items: list[CertificateAdminResponse]
    total: int
    page: int
    page_size: int
    pages: int


class MemberCertificateListResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    items: list[CertificateMemberResponse]
    total: int
    page: int
    page_size: int
    pages: int


class PublicCertificateWork(BaseModel):
    """The certified (snapshot) version of the work behind a certificate.

    Sourced from the approved certification snapshot — never from the work's
    current state — so later edits cannot rewrite what was reviewed. Populated
    only while the work remains publicly visible (published + public + owner
    profile public); otherwise the certificate still verifies with no work
    section. Media is referenced by id and resolved through the public media
    route; no storage keys, internal ids or member PII are exposed.
    """

    model_config = ConfigDict(extra="forbid")

    title: str
    summary: str
    cover_media_id: str | None
    tags: list[str]
    external_links: list[ExternalLink]
    content: ContentDocument
    author: WorkPublicAuthor
    member_profile_url: str | None
    certified_at: datetime
    #: Link to the work's *current* published version, when one still exists.
    current_work_url: str | None
    #: True when the work has been edited since the certified snapshot.
    has_newer_version: bool


class PublicCertificateResponse(BaseModel):
    """Public verification projection — no private work content or PII."""

    model_config = ConfigDict(extra="forbid")

    certificate_id: str
    status: CertificateStatus
    issued_at: datetime
    member_name: str
    work_title: str
    work_url: str | None
    revoked_at: datetime | None
    revocation_reason: str | None
    #: The certified work presentation, or null when not publicly showable.
    work: PublicCertificateWork | None = None


class CertificateEmailResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    certificate_id: str
    email_status: CertificateEmailStatus
    email_sent_at: datetime | None
    message: str
