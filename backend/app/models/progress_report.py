"""Member progress-report domain model (Project Progress Reports).

A progress report is a short, member-authored update about meaningful work on a
*project* activity. Only a **confirmed participant** of a project may submit a
report for it — membership is resolved from the authoritative
`activity_participations` record, never from client input.

Reports move through a deliberately short review lifecycle:

    pending ──approve──────────▶ approved
        └───request_changes──▶ changes_requested ──(author edits/resubmits)──▶ pending

An author may edit and resubmit a report while it is not yet finalised
(`pending` or `changes_requested`); every admin decision is *appended* to
`review_history` — never overwritten — so the full review trail (who, when,
decision, feedback) is preserved across resubmissions.

Only `approved` reports count as the member's official contribution history. A
report is never automatically published to the public portfolio: reports are a
member-portal (private) surface, and the contribution history derived from them
respects that.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, ConfigDict, Field

MAX_DESCRIPTION_LENGTH = 500
MAX_EVIDENCE_LINKS = 10
MAX_URL_LENGTH = 2000
MAX_FEEDBACK_LENGTH = 2000


class ReportStatus(str, Enum):
    """Review lifecycle of a progress report."""

    PENDING = "pending"
    CHANGES_REQUESTED = "changes_requested"
    APPROVED = "approved"


class ReportReviewEntry(BaseModel):
    """One immutable admin decision, appended to a report's review history.

    `version` records the report-content version that was reviewed, so a later
    author edit ("changed since review") is derivable without trusting
    timestamps alone.
    """

    model_config = ConfigDict(extra="forbid")

    status: ReportStatus
    reviewer_id: str
    reviewer_name: str | None = None
    feedback: str | None = None
    version: int
    decided_at: datetime


class ProgressReport(BaseModel):
    """Internal progress-report representation. Never serialised directly —
    response schemas live in the reports module."""

    model_config = ConfigDict(extra="forbid")

    id: str
    # Project (activity) the report belongs to, plus display snapshots so a
    # report stays readable even if the activity is later renamed or removed.
    activity_id: str
    activity_slug: str
    activity_title: str
    # Author — always taken from the authenticated member session.
    member_id: str  # internal Mongo id of the member
    member_readable_id: str  # THL-M-YYYY-NNNN
    role: str | None = None  # participant's project role (snapshot)
    description: str
    evidence_links: list[str] = Field(default_factory=list)
    status: ReportStatus = ReportStatus.PENDING
    # Content version — incremented on every author edit, never by a review.
    version: int = 0
    # Optional idempotency key supplied by the client so a double-click or a
    # retried request cannot create two identical reports.
    client_request_id: str | None = None
    submitted_at: datetime
    updated_at: datetime
    # Latest decision (convenience); the full trail lives in `review_history`.
    reviewed_at: datetime | None = None
    reviewed_by: str | None = None
    review_feedback: str | None = None
    review_history: list[ReportReviewEntry] = Field(default_factory=list)
