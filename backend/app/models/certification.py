"""Certification-review domain model.

A member may request a certification review for one of their published works.
Each request freezes an immutable snapshot of the work at submission time; the
reviewer only ever judges that snapshot. At most one *active* request may exist
per work (enforced by a partial unique index on `{work_id: 1}` where
`active: true`) — approved/rejected requests are deactivated, freeing the slot
for a fresh request, while a `changes_requested` request stays active so the
member can resubmit without creating a new review.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, ConfigDict, Field

from app.models.work import ContentDocument, ExternalLink


class CertificationStatus(str, Enum):
    SUBMITTED = "submitted"
    UNDER_REVIEW = "under_review"
    CHANGES_REQUESTED = "changes_requested"
    APPROVED = "approved"
    REJECTED = "rejected"


TERMINAL_STATUSES: frozenset[CertificationStatus] = frozenset(
    {CertificationStatus.APPROVED, CertificationStatus.REJECTED}
)

#: Statuses that keep the partial unique index slot occupied.
ACTIVE_STATUSES: frozenset[CertificationStatus] = frozenset(
    {
        CertificationStatus.SUBMITTED,
        CertificationStatus.UNDER_REVIEW,
        CertificationStatus.CHANGES_REQUESTED,
    }
)


class CertificationSnapshot(BaseModel):
    """Frozen copy of the work as it was at submission — never mutated."""

    model_config = ConfigDict(extra="forbid")

    slug: str
    title: str
    summary: str
    cover_media_id: str | None = None
    tags: list[str] = Field(default_factory=list)
    external_links: list[ExternalLink] = Field(default_factory=list)
    content: ContentDocument


class CertificationDecision(BaseModel):
    """One recorded reviewer action; the full history is preserved."""

    model_config = ConfigDict(extra="forbid")

    action: str
    by: str
    by_role: str
    at: datetime
    feedback: str | None = None


class CertificationRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", arbitrary_types_allowed=False)

    id: str
    work_id: str
    member_id: str
    status: CertificationStatus
    active: bool
    # Version of the work captured at submission (kept for the snapshot) and
    # the version the reviewer last ruled on.
    snapshot_version: int
    version_reviewed: int
    snapshot: CertificationSnapshot
    captured_at: datetime
    submitted_at: datetime
    decided_at: datetime | None = None
    decided_by: str | None = None
    decided_by_role: str | None = None
    latest_feedback: str | None = None
    decisions: list[CertificationDecision] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime
