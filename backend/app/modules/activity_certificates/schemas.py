"""Pydantic schemas for the activity-certificate API.

Response schemas never expose the private storage object key, Mongo `_id`, or
internal notes. The public verification response is a hand-picked projection.
"""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.activity_certificate import (
    MAX_AWARD_STATEMENT_LENGTH,
    MAX_CUSTOM_AWARD_LABEL_LENGTH,
    MAX_REVOCATION_REASON_LENGTH,
    ActivityAwardCategory,
    ActivityCertificate,
    ActivityCertificateAuditAction,
    ActivityCertificateAuditEntry,
    ActivityCertificateEmailStatus,
    ActivityCertificateStatus,
    ActivityCertificateTemplate,
)

MAX_BULK_RECIPIENTS = 500


# ---------------------------------------------------------------------------
# Requests
# ---------------------------------------------------------------------------
class ActivityCertificateIssueRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    activity_id: str = Field(min_length=1, max_length=64)
    member_id: str = Field(min_length=1, max_length=64)
    award_category: ActivityAwardCategory = ActivityAwardCategory.PARTICIPATION
    custom_award_label: str | None = Field(
        default=None, max_length=MAX_CUSTOM_AWARD_LABEL_LENGTH
    )
    custom_statement: str | None = Field(
        default=None, max_length=MAX_AWARD_STATEMENT_LENGTH
    )
    work_id: str | None = Field(default=None, max_length=64)


class ActivityCertificateBulkRecipient(BaseModel):
    model_config = ConfigDict(extra="forbid")

    member_id: str = Field(min_length=1, max_length=64)
    award_category: ActivityAwardCategory | None = None
    custom_award_label: str | None = Field(
        default=None, max_length=MAX_CUSTOM_AWARD_LABEL_LENGTH
    )
    custom_statement: str | None = Field(
        default=None, max_length=MAX_AWARD_STATEMENT_LENGTH
    )
    work_id: str | None = Field(default=None, max_length=64)


class ActivityCertificateBulkIssueRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    activity_id: str = Field(min_length=1, max_length=64)
    award_category: ActivityAwardCategory = ActivityAwardCategory.PARTICIPATION
    recipients: list[ActivityCertificateBulkRecipient] = Field(
        min_length=1, max_length=MAX_BULK_RECIPIENTS
    )


class ActivityCertificateRevokeRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    reason: str = Field(min_length=1, max_length=MAX_REVOCATION_REASON_LENGTH)

    def clean_reason(self) -> str:
        return self.reason.strip()


class ActivityCertificateTemplateUpdateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    heading: str = Field(min_length=1, max_length=120)
    presentation_line: str = Field(min_length=1, max_length=160)
    award_line: str = Field(min_length=1, max_length=160)
    scope_statement: str = Field(min_length=1, max_length=1000)
    footer_note: str = Field(min_length=1, max_length=120)
    award_labels: dict[str, str] = Field(default_factory=dict)
    award_statements: dict[str, str] = Field(default_factory=dict)

    def to_template(self) -> ActivityCertificateTemplate:
        defaults = ActivityCertificateTemplate()
        labels = dict(defaults.award_labels)
        for key, value in self.award_labels.items():
            if key in labels and value.strip():
                labels[key] = value.strip()[:MAX_CUSTOM_AWARD_LABEL_LENGTH]
        statements = dict(defaults.award_statements)
        for key, value in self.award_statements.items():
            if key in statements and value.strip():
                statements[key] = value.strip()[:MAX_AWARD_STATEMENT_LENGTH]
        return ActivityCertificateTemplate(
            heading=self.heading.strip(),
            presentation_line=self.presentation_line.strip(),
            award_line=self.award_line.strip(),
            scope_statement=self.scope_statement.strip(),
            footer_note=self.footer_note.strip(),
            award_labels=labels,
            award_statements=statements,
        )


# ---------------------------------------------------------------------------
# Responses
# ---------------------------------------------------------------------------
def _download_path(certificate: ActivityCertificate, *, scope: str) -> str:
    return f"/{scope}/activity-certificates/{certificate.certificate_id}/download"


class ActivityCertificateMemberResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    certificate_id: str
    activity_title: str
    activity_slug: str
    activity_type: str
    award_category: str
    award_label: str
    award_statement: str
    member_name: str
    work_title: str | None
    status: ActivityCertificateStatus
    issued_at: datetime
    revoked_at: datetime | None
    revocation_reason: str | None
    email_status: ActivityCertificateEmailStatus
    email_sent_at: datetime | None
    pdf_filename: str
    pdf_size_bytes: int
    verify_url: str
    download_path: str

    @classmethod
    def from_certificate(
        cls, certificate: ActivityCertificate
    ) -> "ActivityCertificateMemberResponse":
        return cls(
            certificate_id=certificate.certificate_id,
            activity_title=certificate.activity_title,
            activity_slug=certificate.activity_slug,
            activity_type=certificate.activity_type,
            award_category=certificate.award_category,
            award_label=certificate.award_label,
            award_statement=certificate.award_statement,
            member_name=certificate.member_name,
            work_title=certificate.work_title,
            status=certificate.status,
            issued_at=certificate.issued_at,
            revoked_at=certificate.revoked_at,
            revocation_reason=(
                certificate.revocation_reason
                if certificate.status == ActivityCertificateStatus.REVOKED
                else None
            ),
            email_status=certificate.email_status,
            email_sent_at=certificate.email_sent_at,
            pdf_filename=certificate.pdf_filename,
            pdf_size_bytes=certificate.pdf_size_bytes,
            verify_url=certificate.qr_verify_url,
            download_path=_download_path(certificate, scope="member"),
        )


class ActivityCertificateAdminResponse(ActivityCertificateMemberResponse):
    activity_id: str
    member_id: str
    member_readable_id: str
    work_id: str | None
    issued_by: str
    issued_by_role: str
    template_version: str
    email_attempts: int
    email_last_error: str | None

    @classmethod
    def from_certificate(
        cls, certificate: ActivityCertificate
    ) -> "ActivityCertificateAdminResponse":
        return cls(
            certificate_id=certificate.certificate_id,
            activity_id=certificate.activity_id,
            activity_title=certificate.activity_title,
            activity_slug=certificate.activity_slug,
            activity_type=certificate.activity_type,
            award_category=certificate.award_category,
            award_label=certificate.award_label,
            award_statement=certificate.award_statement,
            member_id=certificate.member_id,
            member_readable_id=certificate.member_readable_id,
            member_name=certificate.member_name,
            work_id=certificate.work_id,
            work_title=certificate.work_title,
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
            template_version=certificate.template_version,
            email_attempts=certificate.email_attempts,
            email_last_error=certificate.email_last_error,
        )


class ActivityCertificateListResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    items: list[ActivityCertificateAdminResponse]
    total: int
    page: int
    page_size: int
    pages: int


class MemberActivityCertificateListResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    items: list[ActivityCertificateMemberResponse]
    total: int
    page: int
    page_size: int
    pages: int


class ActivityCertificateBulkSkipped(BaseModel):
    model_config = ConfigDict(extra="forbid")

    member_id: str
    certificate_id: str | None = None
    reason: str


class ActivityCertificateBulkFailed(BaseModel):
    model_config = ConfigDict(extra="forbid")

    member_id: str
    reason: str


class ActivityCertificateBulkResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    issued: list[ActivityCertificateAdminResponse]
    skipped: list[ActivityCertificateBulkSkipped]
    failed: list[ActivityCertificateBulkFailed]
    issued_count: int
    skipped_count: int
    failed_count: int


class ActivityCertificateEligibleParticipant(BaseModel):
    model_config = ConfigDict(extra="forbid")

    member_id: str
    member_readable_id: str
    member_name: str
    member_email: str | None
    participation_status: str
    role: str | None
    already_issued_awards: list[str]


class ActivityCertificateEligibleListResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    activity_id: str
    activity_title: str
    items: list[ActivityCertificateEligibleParticipant]


class PublicActivityCertificateWork(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str
    url: str


class PublicActivityCertificateResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    certificate_id: str
    status: ActivityCertificateStatus
    issued_at: datetime
    member_name: str
    activity_title: str
    activity_type: str
    award_category: str
    award_label: str
    award_statement: str
    work: PublicActivityCertificateWork | None = None
    revoked_at: datetime | None
    revocation_reason: str | None


class ActivityCertificateEmailResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    certificate_id: str
    email_status: ActivityCertificateEmailStatus
    email_sent_at: datetime | None
    message: str


class ActivityCertificateTemplateResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    template_version: str
    heading: str
    presentation_line: str
    award_line: str
    scope_statement: str
    footer_note: str
    award_labels: dict[str, str]
    award_statements: dict[str, str]
    updated_by: str | None
    updated_at: datetime | None

    @classmethod
    def from_template(
        cls, template: ActivityCertificateTemplate
    ) -> "ActivityCertificateTemplateResponse":
        return cls(
            template_version=template.template_version,
            heading=template.heading,
            presentation_line=template.presentation_line,
            award_line=template.award_line,
            scope_statement=template.scope_statement,
            footer_note=template.footer_note,
            award_labels=template.award_labels,
            award_statements=template.award_statements,
            updated_by=template.updated_by,
            updated_at=template.updated_at,
        )


class ActivityCertificateAuditResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    action: ActivityCertificateAuditAction
    actor_id: str
    actor_role: str
    detail: str | None
    created_at: datetime

    @classmethod
    def from_entry(
        cls, entry: ActivityCertificateAuditEntry
    ) -> "ActivityCertificateAuditResponse":
        return cls(
            action=entry.action,
            actor_id=entry.actor_id,
            actor_role=entry.actor_role,
            detail=entry.detail,
            created_at=entry.created_at,
        )


DEFAULT_TEMPLATE = ActivityCertificateTemplate()
