"""Activity certificate domain model.

A distinct credential from the Work Recognition Certificate: an **Activity
Certificate** recognizes a *person's participation or award* in an activity
(programme, hackathon, or invitation-only project), not a reviewed work.

Design rules (mirrors the certificates module's guarantees, with its own space):

  * At most one certificate per `(activity, member, award)` — enforced by a
    unique index on `(activity_id, member_id, award_key)`. Distinct awards for
    the same recipient are legitimate and allowed.
  * `certificate_id` (`THL-ACT-CERT-<year>-<random>`) is a public,
    collision-resistant identifier with its own unique index — never derived
    from the sequential database id and never reused, including after
    revocation.
  * The activity, recipient, award and (optional) recognized work are
    **snapshotted** at issuance so later edits cannot rewrite what was issued.
  * The PDF is never stored inside MongoDB: only a private storage object key
    plus integrity metadata.
  * Revocation is a status change with a permanent audit trail — never a delete
    and never an id reuse. Issuance/revocation actions are appended to
    `activity_certificate_audit`.
  * This module never reads or writes the Work Recognition `certificates`
    collection.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, ConfigDict, Field

#: Schema/template identifier stamped on every issued certificate.
ACTIVITY_CERTIFICATE_SCHEMA_VERSION = "1"

#: Public certificate id: `THL-ACT-CERT-<year>-<random>`.
ACTIVITY_CERTIFICATE_ID_PREFIX = "THL-ACT-CERT"

#: Unambiguous alphabet (no 0/O/1/I) so ids are easy to read/type from a PDF.
ACTIVITY_CERTIFICATE_ID_ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"

#: Random suffix length — 12 chars over a 32-symbol alphabet ~= 60 bits.
ACTIVITY_CERTIFICATE_ID_RANDOM_LENGTH = 12

#: Public, non-accreditation scope statement shown on the PDF and verify page.
ACTIVITY_CERTIFICATE_SCOPE_STATEMENT = (
    "Thridha Labs issues this activity certificate to recognise verified "
    "participation or an award in a programme, hackathon or project run by "
    "Thridha Labs. It reflects that participation only and is not a government "
    "credential, university degree, accredited qualification, or employment "
    "guarantee."
)

#: Input bounds.
MAX_REVOCATION_REASON_LENGTH = 1000
MAX_EMAIL_ERROR_LENGTH = 500
MAX_CUSTOM_AWARD_LABEL_LENGTH = 120
MAX_AWARD_STATEMENT_LENGTH = 400


class ActivityCertificateStatus(str, Enum):
    ISSUED = "issued"
    REVOKED = "revoked"


class ActivityCertificateEmailStatus(str, Enum):
    NOT_SENT = "not_sent"
    SENT = "sent"
    FAILED = "failed"


class ActivityAwardCategory(str, Enum):
    """Award categories. `custom` carries an admin-supplied label/statement."""

    FIRST_PLACE = "first_place"
    SECOND_PLACE = "second_place"
    RUNNER_UP = "runner_up"
    PARTICIPATION = "participation"
    CUSTOM = "custom"


class ActivityCertificateAuditAction(str, Enum):
    ISSUED = "issued"
    REVOKED = "revoked"
    EMAIL_SENT = "email_sent"
    EMAIL_FAILED = "email_failed"
    TEMPLATE_UPDATED = "template_updated"


#: Display labels for the fixed categories (overridable in the template).
DEFAULT_AWARD_LABELS: dict[str, str] = {
    ActivityAwardCategory.FIRST_PLACE.value: "First Place",
    ActivityAwardCategory.SECOND_PLACE.value: "Second Place",
    ActivityAwardCategory.RUNNER_UP.value: "Runner-up",
    ActivityAwardCategory.PARTICIPATION.value: "Participation",
}

#: Default statements for the fixed categories (overridable in the template).
DEFAULT_AWARD_STATEMENTS: dict[str, str] = {
    ActivityAwardCategory.FIRST_PLACE.value: (
        "For outstanding performance and a first-place achievement."
    ),
    ActivityAwardCategory.SECOND_PLACE.value: (
        "For excellent performance and a second-place achievement."
    ),
    ActivityAwardCategory.RUNNER_UP.value: (
        "For a strong performance as runner-up."
    ),
    ActivityAwardCategory.PARTICIPATION.value: (
        "For active and valued participation."
    ),
}


def normalize_award_key(category: str, custom_label: str | None) -> str:
    """Canonical dedupe key for one award.

    Fixed categories key by category so the same award cannot be issued twice;
    a custom award keys by its normalized label so two genuinely different
    custom awards for one recipient remain allowed, while a repeated custom
    award is still rejected.
    """
    if category == ActivityAwardCategory.CUSTOM.value:
        normalized = " ".join((custom_label or "").split()).casefold()
        return f"custom:{normalized}"
    return category


def default_award_label(category: str, custom_label: str | None) -> str:
    if category == ActivityAwardCategory.CUSTOM.value:
        return (custom_label or "Special Award").strip()
    return DEFAULT_AWARD_LABELS.get(category, category.replace("_", " ").title())


class ActivityCertificateTemplate(BaseModel):
    """Editable, activity-certificate-only presentation template.

    Stored as a singleton in `activity_certificate_templates`; the resolved
    values are snapshotted onto each certificate so a later template edit never
    changes an already-issued PDF's meaning.
    """

    model_config = ConfigDict(extra="forbid")

    template_version: str = ACTIVITY_CERTIFICATE_SCHEMA_VERSION
    heading: str = "Certificate of Achievement"
    presentation_line: str = "This certificate is presented to"
    award_line: str = "in recognition of verified participation as"
    scope_statement: str = ACTIVITY_CERTIFICATE_SCOPE_STATEMENT
    footer_note: str = "Activity participation ceremony"
    #: category value -> display label (fixed categories only; custom is free).
    award_labels: dict[str, str] = Field(default_factory=lambda: dict(DEFAULT_AWARD_LABELS))
    #: category value -> statement (fixed categories only; custom is free).
    award_statements: dict[str, str] = Field(
        default_factory=lambda: dict(DEFAULT_AWARD_STATEMENTS)
    )
    updated_by: str | None = None
    updated_at: datetime | None = None

    def label_for(self, category: str, custom_label: str | None) -> str:
        if category == ActivityAwardCategory.CUSTOM.value:
            return default_award_label(category, custom_label)
        return self.award_labels.get(category) or default_award_label(category, None)

    def statement_for(self, category: str, custom_statement: str | None) -> str:
        if category == ActivityAwardCategory.CUSTOM.value:
            return (custom_statement or "").strip()
        return self.award_statements.get(category, "")

    def snapshot(self) -> dict:
        """A JSON-safe copy of the fields that affect a rendered certificate."""
        return {
            "template_version": self.template_version,
            "heading": self.heading,
            "presentation_line": self.presentation_line,
            "award_line": self.award_line,
            "scope_statement": self.scope_statement,
            "footer_note": self.footer_note,
            "award_labels": dict(self.award_labels),
            "award_statements": dict(self.award_statements),
        }


class ActivityCertificate(BaseModel):
    """Internal activity-certificate representation. Never serialised directly —
    response schemas live in the activity_certificates module and never expose
    the storage key."""

    model_config = ConfigDict(extra="forbid")

    id: str
    certificate_id: str
    activity_id: str
    #: Snapshotted activity facts (so a later rename does not rewrite history).
    activity_title: str
    activity_slug: str
    activity_type: str
    award_category: str
    award_label: str
    award_statement: str
    #: Canonical dedupe key (category, or `custom:<normalized-label>`).
    award_key: str
    member_id: str
    member_readable_id: str
    member_name: str
    #: Optional recognized work/submission (ownership validated at issuance).
    work_id: str | None = None
    work_title: str | None = None
    work_slug: str | None = None
    status: ActivityCertificateStatus = ActivityCertificateStatus.ISSUED
    template_version: str = ACTIVITY_CERTIFICATE_SCHEMA_VERSION
    #: The resolved template fields actually used to render this certificate.
    template_snapshot: dict = Field(default_factory=dict)
    issued_at: datetime
    issued_by: str
    issued_by_role: str
    pdf_object_key: str
    pdf_filename: str
    pdf_size_bytes: int
    pdf_sha256: str
    qr_verify_url: str
    revoked_at: datetime | None = None
    revoked_by: str | None = None
    revocation_reason: str | None = None
    email_status: ActivityCertificateEmailStatus = ActivityCertificateEmailStatus.NOT_SENT
    email_sent_at: datetime | None = None
    email_last_error: str | None = None
    email_attempts: int = 0
    created_at: datetime
    updated_at: datetime


class ActivityCertificateAuditEntry(BaseModel):
    """One immutable audit event for an activity certificate."""

    model_config = ConfigDict(extra="forbid")

    id: str
    certificate_id: str
    action: ActivityCertificateAuditAction
    actor_id: str
    actor_role: str
    detail: str | None = None
    created_at: datetime
