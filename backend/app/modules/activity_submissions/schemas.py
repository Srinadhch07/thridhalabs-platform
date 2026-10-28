"""Schemas for activity submissions (programme/hackathon, individual only)."""

from __future__ import annotations

from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.core.validators import optional_http_url
from app.models.activity_submission import (
    DELIVERABLE_DESCRIPTION,
    DELIVERABLE_DEMO_URL,
    DELIVERABLE_EVIDENCE_LINKS,
    DELIVERABLE_KINDS,
    DELIVERABLE_REPOSITORY_URL,
    MAX_ATTACHMENTS,
    MAX_DESCRIPTION_LENGTH,
    MAX_EVIDENCE_LINKS,
    MAX_FEEDBACK_LENGTH,
    MAX_TITLE_LENGTH,
    MAX_URL_LENGTH,
    ActivitySubmission,
    ActivitySubmissionKind,
    ActivitySubmissionStatus,
)


def _clean_str(value: str | None) -> str | None:
    if value is None:
        return None
    v = value.strip()
    return v or None


def _http_url(value: str | None) -> str | None:
    if value is None:
        return None
    url = optional_http_url(value)
    if url is None:
        raise ValueError("Must be an http(s) URL")
    return url


def _evidence_links(value: list[str]) -> list[str]:
    if value is None:
        return []
    if len(value) > MAX_EVIDENCE_LINKS:
        raise ValueError(f"Must be at most {MAX_EVIDENCE_LINKS} links")
    cleaned: list[str] = []
    for item in value:
        url = optional_http_url(item)
        if url is not None:
            cleaned.append(url)
    return cleaned


def _media_ids(value: list[str]) -> list[str]:
    if value is None:
        return []
    if len(value) > MAX_ATTACHMENTS:
        raise ValueError(f"Must be at most {MAX_ATTACHMENTS} attachments")
    cleaned: list[str] = []
    for item in value:
        media_id = item.strip()
        if media_id:
            cleaned.append(media_id)
    # Preserve order while removing duplicates.
    return list(dict.fromkeys(cleaned))


# ---------------------------------------------------------------------------
# Requests
# ---------------------------------------------------------------------------
class SubmissionCreateRequest(BaseModel):
    """Create a submission for one activity.

    The author is always the authenticated member; `activity_id` must reference
    a programme/hackathon the member is a *confirmed* participant of.
    """

    model_config = ConfigDict(extra="forbid")

    activity_id: str = Field(min_length=1, max_length=200)
    kind: ActivitySubmissionKind = ActivitySubmissionKind.PROGRESS_UPDATE
    title: str | None = Field(default=None, max_length=MAX_TITLE_LENGTH)
    description: str = Field(max_length=MAX_DESCRIPTION_LENGTH)
    repository_url: str | None = Field(default=None, max_length=MAX_URL_LENGTH)
    demo_url: str | None = Field(default=None, max_length=MAX_URL_LENGTH)
    evidence_links: list[str] = Field(default_factory=list, max_length=MAX_EVIDENCE_LINKS)
    attachment_media_ids: list[str] = Field(default_factory=list, max_length=MAX_ATTACHMENTS)
    client_request_id: str | None = Field(default=None, max_length=200)

    @field_validator("activity_id")
    @classmethod
    def _activity_id(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Activity is required")
        return value

    @field_validator("title")
    @classmethod
    def _title(cls, value: str | None) -> str | None:
        return _clean_str(value)

    @field_validator("description")
    @classmethod
    def _description(cls, value: str) -> str:
        v = value.strip()
        if not v:
            raise ValueError("Description is required")
        if len(v) > MAX_DESCRIPTION_LENGTH:
            raise ValueError(f"Must be at most {MAX_DESCRIPTION_LENGTH} characters")
        return v

    @field_validator("repository_url")
    @classmethod
    def _repo(cls, value: str | None) -> str | None:
        return _http_url(value)

    @field_validator("demo_url")
    @classmethod
    def _demo(cls, value: str | None) -> str | None:
        return _http_url(value)

    @field_validator("evidence_links")
    @classmethod
    def _links(cls, value: list[str]) -> list[str]:
        return _evidence_links(value)

    @field_validator("attachment_media_ids")
    @classmethod
    def _media(cls, value: list[str]) -> list[str]:
        return _media_ids(value)

    @field_validator("client_request_id")
    @classmethod
    def _cid(cls, value: str | None) -> str | None:
        return _clean_str(value)


class SubmissionUpdateRequest(BaseModel):
    """Edit and resubmit a submission while it is not yet finalised."""

    model_config = ConfigDict(extra="forbid")

    title: str | None = Field(default=None, max_length=MAX_TITLE_LENGTH)
    description: str = Field(max_length=MAX_DESCRIPTION_LENGTH)
    repository_url: str | None = Field(default=None, max_length=MAX_URL_LENGTH)
    demo_url: str | None = Field(default=None, max_length=MAX_URL_LENGTH)
    evidence_links: list[str] = Field(default_factory=list, max_length=MAX_EVIDENCE_LINKS)
    attachment_media_ids: list[str] = Field(default_factory=list, max_length=MAX_ATTACHMENTS)

    @field_validator("title")
    @classmethod
    def _title(cls, value: str | None) -> str | None:
        return _clean_str(value)

    @field_validator("description")
    @classmethod
    def _description(cls, value: str) -> str:
        v = value.strip()
        if not v:
            raise ValueError("Description is required")
        if len(v) > MAX_DESCRIPTION_LENGTH:
            raise ValueError(f"Must be at most {MAX_DESCRIPTION_LENGTH} characters")
        return v

    @field_validator("repository_url")
    @classmethod
    def _repo(cls, value: str | None) -> str | None:
        return _http_url(value)

    @field_validator("demo_url")
    @classmethod
    def _demo(cls, value: str | None) -> str | None:
        return _http_url(value)

    @field_validator("evidence_links")
    @classmethod
    def _links(cls, value: list[str]) -> list[str]:
        return _evidence_links(value)

    @field_validator("attachment_media_ids")
    @classmethod
    def _media(cls, value: list[str]) -> list[str]:
        return _media_ids(value)


class SubmissionDecisionRequest(BaseModel):
    """Admin review decision on a submission."""

    model_config = ConfigDict(extra="forbid")

    action: Literal["approve", "request_changes", "reject"]
    feedback: str | None = Field(default=None, max_length=MAX_FEEDBACK_LENGTH)

    def clean_feedback(self) -> str | None:
        if self.feedback is None:
            return None
        cleaned = self.feedback.strip()
        return cleaned or None


# ---------------------------------------------------------------------------
# Responses
# ---------------------------------------------------------------------------
class SubmissionReviewEntryResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: ActivitySubmissionStatus
    reviewer_name: str | None
    feedback: str | None
    version: int
    decided_at: datetime

    @classmethod
    def from_entry(cls, entry) -> "SubmissionReviewEntryResponse":  # noqa: ANN001
        return cls(
            status=entry.status,
            reviewer_name=entry.reviewer_name,
            feedback=entry.feedback,
            version=entry.version,
            decided_at=entry.decided_at,
        )


class SubmissionRevisionResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    version: int
    title: str | None
    description: str
    repository_url: str | None
    demo_url: str | None
    evidence_links: list[str]
    submitted_at: datetime

    @classmethod
    def from_revision(cls, revision) -> "SubmissionRevisionResponse":  # noqa: ANN001
        return cls(
            version=revision.version,
            title=revision.title,
            description=revision.description,
            repository_url=revision.repository_url,
            demo_url=revision.demo_url,
            evidence_links=revision.evidence_links,
            submitted_at=revision.submitted_at,
        )


class ActivitySubmissionResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    activity_id: str
    activity_slug: str
    activity_title: str
    activity_type: str
    member_id: str
    member_readable_id: str
    kind: ActivitySubmissionKind
    title: str | None
    description: str
    repository_url: str | None
    demo_url: str | None
    evidence_links: list[str]
    attachment_media_ids: list[str]
    status: ActivitySubmissionStatus
    version: int
    editable: bool
    submitted_at: datetime
    updated_at: datetime
    reviewed_at: datetime | None
    reviewed_by: str | None
    review_feedback: str | None
    review_history: list[SubmissionReviewEntryResponse]
    revisions: list[SubmissionRevisionResponse]

    @classmethod
    def from_submission(cls, sub: ActivitySubmission) -> "ActivitySubmissionResponse":
        return cls(
            id=sub.id,
            activity_id=sub.activity_id,
            activity_slug=sub.activity_slug,
            activity_title=sub.activity_title,
            activity_type=sub.activity_type,
            member_id=sub.member_id,
            member_readable_id=sub.member_readable_id,
            kind=sub.kind,
            title=sub.title,
            description=sub.description,
            repository_url=sub.repository_url,
            demo_url=sub.demo_url,
            evidence_links=sub.evidence_links,
            attachment_media_ids=sub.attachment_media_ids,
            status=sub.status,
            version=sub.version,
            editable=sub.is_editable,
            submitted_at=sub.submitted_at,
            updated_at=sub.updated_at,
            reviewed_at=sub.reviewed_at,
            reviewed_by=sub.reviewed_by,
            review_feedback=sub.review_feedback,
            review_history=[
                SubmissionReviewEntryResponse.from_entry(entry)
                for entry in sub.review_history
            ],
            revisions=[
                SubmissionRevisionResponse.from_revision(revision)
                for revision in sub.revisions
            ],
        )


class AdminActivitySubmissionResponse(ActivitySubmissionResponse):
    """Admin view of any submission (review queue + detail)."""

    model_config = ConfigDict(extra="forbid")

    member_name: str | None = None
    member_email: str | None = None

    @classmethod
    def from_submission(
        cls,
        sub: ActivitySubmission,
        *,
        member_name: str | None = None,
        member_email: str | None = None,
    ) -> "AdminActivitySubmissionResponse":
        base = ActivitySubmissionResponse.from_submission(sub).model_dump()
        base["member_name"] = member_name
        base["member_email"] = member_email
        return cls(**base)


class SubmissionListResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    items: list[ActivitySubmissionResponse]
    total: int
    page: int
    page_size: int
    pages: int


class AdminSubmissionListResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    items: list[AdminActivitySubmissionResponse]
    total: int
    page: int
    page_size: int
    pages: int


# ---------------------------------------------------------------------------
# Member workspace
# ---------------------------------------------------------------------------
class ActivityTaskResponse(BaseModel):
    """One activity task plus the member's own completion state."""

    model_config = ConfigDict(extra="forbid")

    id: str
    title: str
    description: str
    due_date: date | None
    completed: bool


class ActivityResourceResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    label: str
    url: str


class ActivityWorkspaceResponse(BaseModel):
    """Everything one member needs for one activity workspace."""

    model_config = ConfigDict(extra="forbid")

    activity_id: str
    slug: str
    title: str
    activity_type: str
    summary: str
    description: str
    presentation_status: str
    start_date: date | None
    end_date: date | None
    banner_media_id: str | None
    has_brief: bool
    objectives: list[str]
    instructions: str
    requirements: list[str]
    resources: list[ActivityResourceResponse]
    required_deliverables: list[str]
    participation_status: str | None
    participation_role: str | None
    tasks: list[ActivityTaskResponse]
    completed_task_count: int
    task_count: int
    progress_percent: int
    deliverable: ActivitySubmissionResponse | None
    progress_updates: list[ActivitySubmissionResponse]
    can_submit: bool
    submit_blocked_reason: str | None


class ActivityWorkspaceListResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    items: list[ActivityWorkspaceResponse]


class TaskCompletionRequest(BaseModel):
    """Toggle one personal task's completion for the authenticated member."""

    model_config = ConfigDict(extra="forbid")

    task_id: str = Field(min_length=1, max_length=200)
    completed: bool

    @field_validator("task_id")
    @classmethod
    def _task_id(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Task is required")
        return value


class AdminStudentActivityResponse(BaseModel):
    """Admin view of one student's record inside one activity."""

    model_config = ConfigDict(extra="forbid")

    activity_id: str
    activity_slug: str
    activity_title: str
    activity_type: str
    member_id: str
    member_readable_id: str
    member_name: str | None
    member_email: str | None
    participation_status: str
    participation_role: str | None
    participation_source: str
    confirmed_at: datetime | None
    tasks: list[ActivityTaskResponse]
    completed_task_count: int
    task_count: int
    progress_percent: int
    submissions: list[AdminActivitySubmissionResponse]


#: Exposed so the member workspace can explain what an activity expects.
REQUIRED_DELIVERABLE_LABELS: dict[str, str] = {
    DELIVERABLE_DESCRIPTION: "Description",
    DELIVERABLE_REPOSITORY_URL: "Repository URL",
    DELIVERABLE_DEMO_URL: "Demo URL",
    DELIVERABLE_EVIDENCE_LINKS: "Evidence links",
}

__all__ = [
    "DELIVERABLE_KINDS",
    "REQUIRED_DELIVERABLE_LABELS",
    "ActivityResourceResponse",
    "ActivitySubmissionResponse",
    "ActivityTaskResponse",
    "ActivityWorkspaceListResponse",
    "ActivityWorkspaceResponse",
    "AdminActivitySubmissionResponse",
    "AdminStudentActivityResponse",
    "AdminSubmissionListResponse",
    "SubmissionCreateRequest",
    "SubmissionDecisionRequest",
    "SubmissionListResponse",
    "SubmissionReviewEntryResponse",
    "SubmissionRevisionResponse",
    "SubmissionUpdateRequest",
    "TaskCompletionRequest",
]
