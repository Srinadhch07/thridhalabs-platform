"""Pydantic schemas for the activities API (admin + public + member).

Public responses never expose drafts, cancelled or archived internals beyond the
derived presentation label, and never leak internal Mongo ids or the stored
brief object key — the brief is referenced by `has_brief` / version metadata and
served through a controlled route.
"""

from __future__ import annotations

from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.core.validators import non_empty_name
from app.models.activity import (
    ActivityPresentationStatus,
    ActivityResource,
    ActivityStatus,
    ActivityTask,
    ActivityType,
    ParticipationSource,
    ParticipationStatus,
)

MAX_TEXT_LENGTH = 8000
MAX_ROLES = 40
MAX_ROLE_LENGTH = 100
MAX_TAGS = 20
MAX_TAG_LENGTH = 40
MAX_INVITATIONS = 200
MAX_OBJECTIVES = 20
MAX_REQUIREMENTS = 20
MAX_RESOURCES = 20
MAX_TASKS = 30
MAX_RESOURCE_LABEL_LENGTH = 120
MAX_RESOURCE_URL_LENGTH = 2000
MAX_TASK_TITLE_LENGTH = 150
MAX_TASK_DESCRIPTION_LENGTH = 2000


def _clean_strings(value: list[str], *, max_items: int, item_max: int) -> list[str]:
    cleaned = [item.strip()[:item_max] for item in value if item.strip()]
    return list(dict.fromkeys(cleaned))[:max_items]


def _clean_resources(value: list[ActivityResource]) -> list[ActivityResource]:
    seen: set[str] = set()
    out: list[ActivityResource] = []
    for item in value[:MAX_RESOURCES]:
        label = item.label.strip()[:MAX_RESOURCE_LABEL_LENGTH]
        url = item.url.strip()[:MAX_RESOURCE_URL_LENGTH]
        if not label or not url:
            continue
        if not url.startswith(("http://", "https://")):
            raise ValueError("Resource URLs must be http(s)")
        if url in seen:
            continue
        seen.add(url)
        out.append(ActivityResource(label=label, url=url))
    return out


def _clean_tasks(value: list[ActivityTask]) -> list[ActivityTask]:
    seen: set[str] = set()
    out: list[ActivityTask] = []
    for item in value[:MAX_TASKS]:
        task_id = item.id.strip()
        title = item.title.strip()[:MAX_TASK_TITLE_LENGTH]
        if not task_id or not title:
            continue
        if task_id in seen:
            raise ValueError("Task ids must be unique within an activity")
        seen.add(task_id)
        out.append(
            ActivityTask(
                id=task_id,
                title=title,
                description=item.description.strip()[:MAX_TASK_DESCRIPTION_LENGTH],
                due_date=item.due_date,
            )
        )
    return out


def _clean_deliverables(value: list[str]) -> list[str]:
    from app.models.activity_submission import DELIVERABLE_KINDS

    out: list[str] = []
    for item in value:
        key = item.strip()
        if not key:
            continue
        if key not in DELIVERABLE_KINDS:
            raise ValueError(
                "Required deliverables must be one of: " + ", ".join(DELIVERABLE_KINDS)
            )
        if key not in out:
            out.append(key)
    return out


def _validate_dates(start: date | None, end: date | None) -> None:
    if start is not None and end is not None and end < start:
        raise ValueError("end_date must not be before start_date")


# ---------------------------------------------------------------------------
# Writes (admin)
# ---------------------------------------------------------------------------
class ActivityCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str
    slug: str | None = None
    activity_type: ActivityType
    summary: str = Field(default="", max_length=500)
    description: str = Field(default="", max_length=MAX_TEXT_LENGTH)
    status: ActivityStatus = ActivityStatus.DRAFT
    start_date: date | None = None
    end_date: date | None = None
    banner_media_id: str | None = None
    featured: bool = False
    display_order: int = Field(default=0, ge=0)
    roles_offered: list[str] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)
    objectives: list[str] = Field(default_factory=list)
    instructions: str = Field(default="", max_length=MAX_TEXT_LENGTH)
    requirements: list[str] = Field(default_factory=list)
    resources: list[ActivityResource] = Field(default_factory=list)
    tasks: list[ActivityTask] = Field(default_factory=list)
    required_deliverables: list[str] = Field(default_factory=list)
    cancel_reason: str | None = Field(default=None, max_length=500)

    @field_validator("title")
    @classmethod
    def _title(cls, value: str) -> str:
        return non_empty_name(value)

    @field_validator("roles_offered")
    @classmethod
    def _roles(cls, value: list[str]) -> list[str]:
        return _clean_strings(value, max_items=MAX_ROLES, item_max=MAX_ROLE_LENGTH)

    @field_validator("tags")
    @classmethod
    def _tags(cls, value: list[str]) -> list[str]:
        return _clean_strings(value, max_items=MAX_TAGS, item_max=MAX_TAG_LENGTH)

    @field_validator("objectives")
    @classmethod
    def _objectives(cls, value: list[str]) -> list[str]:
        return _clean_strings(value, max_items=MAX_OBJECTIVES, item_max=MAX_TEXT_LENGTH)

    @field_validator("requirements")
    @classmethod
    def _requirements(cls, value: list[str]) -> list[str]:
        return _clean_strings(
            value, max_items=MAX_REQUIREMENTS, item_max=MAX_TEXT_LENGTH
        )

    @field_validator("resources")
    @classmethod
    def _resources(cls, value: list[ActivityResource]) -> list[ActivityResource]:
        return _clean_resources(value)

    @field_validator("tasks")
    @classmethod
    def _tasks(cls, value: list[ActivityTask]) -> list[ActivityTask]:
        return _clean_tasks(value)

    @field_validator("required_deliverables")
    @classmethod
    def _required_deliverables(cls, value: list[str]) -> list[str]:
        return _clean_deliverables(value)

    @model_validator(mode="after")
    def _dates(self) -> "ActivityCreate":
        _validate_dates(self.start_date, self.end_date)
        return self


class ActivityUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str | None = None
    slug: str | None = None
    activity_type: ActivityType | None = None
    summary: str | None = Field(default=None, max_length=500)
    description: str | None = Field(default=None, max_length=MAX_TEXT_LENGTH)
    status: ActivityStatus | None = None
    start_date: date | None = None
    end_date: date | None = None
    banner_media_id: str | None = None
    featured: bool | None = None
    display_order: int | None = Field(default=None, ge=0)
    roles_offered: list[str] | None = None
    tags: list[str] | None = None
    objectives: list[str] | None = None
    instructions: str | None = Field(default=None, max_length=MAX_TEXT_LENGTH)
    requirements: list[str] | None = None
    resources: list[ActivityResource] | None = None
    tasks: list[ActivityTask] | None = None
    required_deliverables: list[str] | None = None
    cancel_reason: str | None = Field(default=None, max_length=500)

    @field_validator("title")
    @classmethod
    def _title(cls, value: str | None) -> str | None:
        return non_empty_name(value) if value is not None else None

    @field_validator("roles_offered")
    @classmethod
    def _roles(cls, value: list[str] | None) -> list[str] | None:
        if value is None:
            return None
        return _clean_strings(value, max_items=MAX_ROLES, item_max=MAX_ROLE_LENGTH)

    @field_validator("tags")
    @classmethod
    def _tags(cls, value: list[str] | None) -> list[str] | None:
        if value is None:
            return None
        return _clean_strings(value, max_items=MAX_TAGS, item_max=MAX_TAG_LENGTH)

    @field_validator("objectives")
    @classmethod
    def _objectives(cls, value: list[str] | None) -> list[str] | None:
        if value is None:
            return None
        return _clean_strings(value, max_items=MAX_OBJECTIVES, item_max=MAX_TEXT_LENGTH)

    @field_validator("requirements")
    @classmethod
    def _requirements(cls, value: list[str] | None) -> list[str] | None:
        if value is None:
            return None
        return _clean_strings(
            value, max_items=MAX_REQUIREMENTS, item_max=MAX_TEXT_LENGTH
        )

    @field_validator("resources")
    @classmethod
    def _resources(
        cls, value: list[ActivityResource] | None
    ) -> list[ActivityResource] | None:
        if value is None:
            return None
        return _clean_resources(value)

    @field_validator("tasks")
    @classmethod
    def _tasks(cls, value: list[ActivityTask] | None) -> list[ActivityTask] | None:
        if value is None:
            return None
        return _clean_tasks(value)

    @field_validator("required_deliverables")
    @classmethod
    def _required_deliverables(cls, value: list[str] | None) -> list[str] | None:
        if value is None:
            return None
        return _clean_deliverables(value)


# ---------------------------------------------------------------------------
# Invitations + participants (admin)
# ---------------------------------------------------------------------------
class InvitationItem(BaseModel):
    model_config = ConfigDict(extra="forbid")

    member_id: str
    role: str | None = Field(default=None, max_length=MAX_ROLE_LENGTH)


class InvitationRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    invitations: list[InvitationItem] = Field(min_length=1, max_length=MAX_INVITATIONS)
    subject: str | None = Field(default=None, max_length=200)
    message: str | None = Field(default=None, max_length=MAX_TEXT_LENGTH)


class InvitationResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    invited: int
    re_invited: int
    emails_sent: int
    email_failures: int
    skipped: list[str]
    errors: list[str]


class ParticipantUpdateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: ParticipationStatus | None = None
    role: str | None = Field(default=None, max_length=MAX_ROLE_LENGTH)
    note: str | None = Field(default=None, max_length=1000)


# ---------------------------------------------------------------------------
# Responses
# ---------------------------------------------------------------------------
class BriefResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    version: int
    filename: str
    size_bytes: int
    uploaded_at: datetime


class ActivityAdminResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    title: str
    slug: str
    activity_type: ActivityType
    summary: str
    description: str
    status: ActivityStatus
    presentation_status: ActivityPresentationStatus
    start_date: date | None
    end_date: date | None
    banner_media_id: str | None
    featured: bool
    display_order: int
    roles_offered: list[str]
    tags: list[str]
    objectives: list[str]
    instructions: str
    requirements: list[str]
    resources: list[ActivityResource]
    tasks: list[ActivityTask]
    required_deliverables: list[str]
    brief: BriefResponse | None
    brief_history_count: int
    cancel_reason: str | None
    participant_counts: dict[str, int]
    created_at: datetime
    updated_at: datetime
    published_at: datetime | None
    cancelled_at: datetime | None
    archived_at: datetime | None


class ActivityAdminListResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    items: list[ActivityAdminResponse]
    total: int
    page: int
    page_size: int
    pages: int


class ParticipantResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    activity_id: str
    member_id: str
    member_readable_id: str
    member_name: str | None
    member_email: str | None
    role: str | None
    status: ParticipationStatus
    source: ParticipationSource
    note: str | None
    invited_at: datetime | None
    responded_at: datetime | None
    confirmed_at: datetime | None
    withdrawn_at: datetime | None
    email_sent_at: datetime | None
    created_at: datetime
    updated_at: datetime


class ParticipantListResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    items: list[ParticipantResponse]
    total: int
    page: int
    page_size: int
    pages: int


class ActivityPublicResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    slug: str
    title: str
    activity_type: ActivityType
    summary: str
    description: str
    presentation_status: ActivityPresentationStatus
    start_date: date | None
    end_date: date | None
    banner_media_id: str | None
    featured: bool
    display_order: int
    roles_offered: list[str]
    tags: list[str]
    has_brief: bool
    registration_open: bool


class ActivityPublicListResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    items: list[ActivityPublicResponse]
    total: int
    page: int
    page_size: int
    pages: int


class MemberActivityResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    slug: str
    title: str
    activity_type: ActivityType
    summary: str
    presentation_status: ActivityPresentationStatus
    start_date: date | None
    end_date: date | None
    banner_media_id: str | None
    has_brief: bool
    registration_open: bool
    can_register: bool
    can_withdraw: bool
    participation_status: ParticipationStatus | None
    participation_role: str | None


class MemberActivityListResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    items: list[MemberActivityResponse]
