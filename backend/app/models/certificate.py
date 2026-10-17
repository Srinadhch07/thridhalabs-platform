"""Certificate domain model.

A certificate is issued by an authorized administrator for a *specific
certification request* whose work was reviewed and approved. It records the
immutable facts of that recognition (member name, work title/slug at issuance,
decision + issue timestamps, the reviewer) plus the durable PDF storage
reference and email-delivery state.

Design rules:
  * One certificate per certification request (enforced by a unique index on
    `request_id`); duplicate/concurrent issuance is idempotent.
  * `certificate_id` is a public, collision-resistant identifier with its own
    unique index — never derived from the sequential database id and never
    reused, including after revocation.
  * The PDF itself is never stored inside MongoDB: only a storage object key
    (private) and its integrity metadata are kept.
  * Revocation is a status change with a permanent audit trail — the record is
    never deleted and the id is never recycled.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, ConfigDict

#: Schema/template identifier stamped on every issued certificate.
CERTIFICATE_SCHEMA_VERSION = "1"

#: Public certificate id: `THL-CERT-<year>-<random>`.
CERTIFICATE_ID_PREFIX = "THL-CERT"

#: Unambiguous alphabet (no 0/O/1/I) so ids are easy to read/type from a PDF.
CERTIFICATE_ID_ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"

#: Random suffix length — 12 chars over a 32-symbol alphabet ≈ 60 bits.
CERTIFICATE_ID_RANDOM_LENGTH = 12

#: Public, non-accreditation scope statement shown on the PDF and verify page.
CERTIFICATE_SCOPE_STATEMENT = (
    "Thridha Labs recognizes this work following an internal review of the "
    "submitted work and its associated presentation. This recognition applies "
    "only to the reviewed work; it is not a government credential, university "
    "degree, accredited qualification, or employment guarantee."
)


class CertificateStatus(str, Enum):
    ISSUED = "issued"
    REVOKED = "revoked"


class CertificateEmailStatus(str, Enum):
    NOT_SENT = "not_sent"
    SENT = "sent"
    FAILED = "failed"


class Certificate(BaseModel):
    """Internal certificate representation. Never serialised directly — response
    schemas live in the certificates module and never expose the storage key."""

    model_config = ConfigDict(extra="forbid")

    id: str
    certificate_id: str
    request_id: str
    work_id: str
    member_id: str
    #: Readable member id (THL-M-YYYY-NNNN) captured at issuance for the public
    #: work URL; the internal id above is used for ownership checks.
    member_readable_id: str
    member_name: str
    work_title: str
    work_slug: str
    status: CertificateStatus = CertificateStatus.ISSUED
    template_version: str = CERTIFICATE_SCHEMA_VERSION
    decided_at: datetime | None = None
    issued_at: datetime
    issued_by: str
    issued_by_role: str
    #: Private storage object key for the official PDF (never exposed publicly).
    pdf_object_key: str
    pdf_filename: str
    pdf_size_bytes: int
    pdf_sha256: str
    #: The exact URL encoded into the PDF QR code (kept for verification/audit).
    qr_verify_url: str
    revoked_at: datetime | None = None
    revoked_by: str | None = None
    revocation_reason: str | None = None
    email_status: CertificateEmailStatus = CertificateEmailStatus.NOT_SENT
    email_sent_at: datetime | None = None
    email_last_error: str | None = None
    email_attempts: int = 0
    created_at: datetime
    updated_at: datetime


class CertificateRef(BaseModel):
    """Lightweight certificate state attached to a certification request."""

    model_config = ConfigDict(extra="forbid")

    certificate_id: str
    status: CertificateStatus
    issued_at: datetime
    email_status: CertificateEmailStatus
    work_title: str
    revoked_at: datetime | None = None


# Input bounds shared by the schemas.
MAX_REVOCATION_REASON_LENGTH = 1000
MAX_EMAIL_ERROR_LENGTH = 500

