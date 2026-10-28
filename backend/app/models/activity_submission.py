"""Activity workspace submissions (Programmes and Hackathons).

Individual participation only: one student owns their own submissions for an
activity. There is deliberately no team/member-group concept in this module.

Two kinds of submission exist:

- `progress_update` — a short, dated update about work in progress. A student
  may file many of them over the life of the activity.
- `deliverable` — the individual work product (project description, repository
  URL, demo URL, evidence links and optional media attachments). A student has
  at most one deliverable per activity; it can be edited and resubmitted while
  it has not been finalised.

Admin review decisions move a submission through the same short lifecycle used
by the Project Progress Reports module:

    pending ──approve──────────▶ approved
        └───request_changes──▶ changes_requested ──(student resubmits)──▶ pending
        └───reject────────────▶ rejected

Every admin decision is *appended* to `review_history` so the full trail is
preserved across resubmissions. Approved and rejected submissions are final.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

MAX_TITLE_LENGTH = 150
MAX_DESCRIPTION_LENGTH = 5000
MAX_FEEDBACK_LENGTH = 2000
MAX_URL_LENGTH = 2000
MAX_EVIDENCE_LINKS = 10
MAX_ATTACHMENTS = 10
MAX_REVISIONS = 20

#: Deliverable parts an admin may require from a participant.
DELIVERABLE_DESCRIPTION = "description"
DELIVERABLE_REPOSITORY_URL = "repository_url"
DELIVERABLE_DEMO_URL = "demo_url"
DELIVERABLE_EVIDENCE_LINKS = "evidence_links"

#: Every accepted value of `Activity.required_deliverables`.
DELIVERABLE_KINDS: tuple[str, ...] = (
    DELIVERABLE_DESCRIPTION,
    DELIVERABLE_REPOSITORY_URL,
    DELIVERABLE_DEMO_URL,
    DELIVERABLE_EVIDENCE_LINKS,
)

#: Human labels for the admin interface.
DELIVERABLE_LABELS: dict[str, str] = {
    DELIVERABLE_DESCRIPTION: "Description",
    DELIVERABLE_REPOSITORY_URL: "Repository URL",
    DELIVERABLE_DEMO_URL: "Demo URL",
    DELIVERABLE_EVIDENCE_LINKS: "Evidence links",
}


class ActivitySubmissionKind(str, Enum):
    """What a submission represents."""

    PROGRESS_UPDATE = "progress_update"
    DELIVERABLE = "deliverable"


class ActivitySubmissionStatus(str, Enum):
    """Review lifecycle of an individual activity submission."""

    PENDING = "pending"
    CHANGES_REQUESTED = "changes_requested"
    APPROVED = "approved"
    REJECTED = "rejected"


#: Statuses a student may still edit/resubmit.
EDITABLE_STATUSES = frozenset(
    {
        ActivitySubmissionStatus.PENDING.value,
        ActivitySubmissionStatus.CHANGES_REQUESTED.value,
    }
)

#: Statuses that finalise a submission (no further student edits).
FINAL_STATUSES = frozenset(
    {ActivitySubmissionStatus.APPROVED.value, ActivitySubmissionStatus.REJECTED.value}
)


class ActivitySubmissionReviewEntry(BaseModel):
    """One immutable admin decision appended to a submission's review trail."""

    model_config = ConfigDict(extra="forbid")

    status: ActivitySubmissionStatus
    reviewer_id: str
    reviewer_name: str | None = None
    feedback: str | None = None
    version: int = 0
    decided_at: datetime


class ActivitySubmissionAttachment(BaseModel):
    """A member-owned media file attached to an individual submission.

    Attachments are stored as metadata only (the bytes live in the platform's
    media pipeline); `media_id` points at the stored object.
    """

    model_config = ConfigDict(extra="forbid")

    media_id: str
    filename: str
    size_bytes: int = 0
    mime_type: str | None = None
    uploaded_at: datetime | None = None


class ActivitySubmissionRevision(BaseModel):
    """A snapshot of the content a student submitted in an earlier version.

    Resubmitting a deliverable keeps the previous version here so the member
    can see their own submission history.
    """

    model_config = ConfigDict(extra="forbid")

    version: int
    title: str | None = None
    description: str = ""
    repository_url: str | None = None
    demo_url: str | None = None
    evidence_links: list[str] = Field(default_factory=list)
    attachment_media_ids: list[str] = Field(default_factory=list)
    submitted_at: datetime


class ActivitySubmission(BaseModel):
    """Internal representation. Never serialised directly - response schemas
    live in the `activity_submissions` module."""

    model_config = ConfigDict(extra="forbid")

    id: str
    # Activity the submission belongs to (+ display snapshots).
    activity_id: str
    activity_slug: str
    activity_title: str
    activity_type: str  # "programme" | "hackathon"
    # Author - always taken from the authenticated member session.
    member_id: str
    member_readable_id: str
    kind: ActivitySubmissionKind = ActivitySubmissionKind.PROGRESS_UPDATE
    title: str | None = None
    description: str
    repository_url: str | None = None
    demo_url: str | None = None
    evidence_links: list[str] = Field(default_factory=list)
    attachment_media_ids: list[str] = Field(default_factory=list)
    status: ActivitySubmissionStatus = ActivitySubmissionStatus.PENDING
    # Content version - incremented on every student edit, never by a review.
    version: int = 0
    # Optional idempotency key supplied by the client.
    client_request_id: str | None = None
    submitted_at: datetime
    updated_at: datetime
    # Latest decision (convenience); full trail lives in `review_history`.
    reviewed_at: datetime | None = None
    reviewed_by: str | None = None
    review_feedback: str | None = None
    review_history: list[ActivitySubmissionReviewEntry] = Field(default_factory=list)
    # Earlier content versions (deliverables only).
    revisions: list[ActivitySubmissionRevision] = Field(default_factory=list)

    @property
    def is_editable(self) -> bool:
        return self.status.value in EDITABLE_STATUSES

    @property
    def is_final(self) -> bool:
        return self.status.value in FINAL_STATUSES


def attachments_from_doc(value: Any) -> list[dict]:
    """Normalise persisted attachment metadata into plain dicts."""
    if not value:
        return []
    if isinstance(value, list):
        return [dict(item) for item in value if isinstance(item, dict)]
    return []
