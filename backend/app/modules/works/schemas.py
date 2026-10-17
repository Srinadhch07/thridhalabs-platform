"""Pydantic schemas for the member works API (member + public surfaces).

API boundaries expose clean models only: never raw MongoDB documents, never the
reader's Mongo `_id`, never internal fields. Public responses carry only what a
visitor is allowed to see and reference media by id (resolved through the
public media route by the frontend).
"""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models.member import ProfileVisibility
from app.models.project import ProjectType
from app.models.work import (
    ContentDocument,
    ExternalLink,
    MAX_SUMMARY_LENGTH,
    MAX_TAGS,
    MAX_TITLE_LENGTH,
    MemberWork,
    WorkPublicationStatus,
    WorkVisibility,
)
from app.modules.members.schemas import _tag_list
from app.core.errors import AppError

MAX_FEEDBACK_LENGTH = 4000

TEMPLATES = ("blank-canvas", "project-showcase", "research", "creative-portfolio")


def _title(value: str) -> str:
    value = value.strip()
    if not value:
        raise ValueError("Title is required")
    if len(value) > MAX_TITLE_LENGTH:
        raise ValueError(f"Must be at most {MAX_TITLE_LENGTH} characters")
    return value


def _summary(value: str) -> str:
    value = value.strip()
    if not value:
        raise ValueError("Summary is required")
    if len(value) > MAX_SUMMARY_LENGTH:
        raise ValueError(f"Must be at most {MAX_SUMMARY_LENGTH} characters")
    return value


def _optional_summary(value: str | None) -> str | None:
    if value is None:
        return None
    value = value.strip()
    if not value:
        raise ValueError("Summary must not be empty when provided")
    if len(value) > MAX_SUMMARY_LENGTH:
        raise ValueError(f"Must be at most {MAX_SUMMARY_LENGTH} characters")
    return value


def _template(value: str | None) -> str | None:
    if value is None:
        return None
    if value not in TEMPLATES:
        raise ValueError(
            f"Template must be one of: {', '.join(TEMPLATES)}"
        )
    return value


class WorkCreateRequest(BaseModel):
    """Create a work. The slug is always backend-generated from the title —
    callers can never choose or spoof it."""

    model_config = ConfigDict(extra="forbid")

    title: str = Field(max_length=MAX_TITLE_LENGTH)
    summary: str = Field(max_length=MAX_SUMMARY_LENGTH)
    template: str | None = None
    cover_media_id: str | None = None
    tags: list[str] = Field(default_factory=list, max_length=MAX_TAGS)
    external_links: list[ExternalLink] = Field(default_factory=list, max_length=20)
    content: ContentDocument | None = None
    visibility: WorkVisibility = WorkVisibility.PRIVATE

    @field_validator("title")
    @classmethod
    def _title(cls, value: str) -> str:
        return _title(value)

    @field_validator("summary")
    @classmethod
    def _summary(cls, value: str) -> str:
        return _summary(value)

    @field_validator("template")
    @classmethod
    def _template(cls, value: str | None) -> str | None:
        return _template(value)

    @field_validator("tags")
    @classmethod
    def _tags(cls, value: list[str]) -> list[str]:
        return _tag_list(value)

    @field_validator("cover_media_id")
    @classmethod
    def _media_id(cls, value: str | None) -> str | None:
        if value is None:
            return None
        value = value.strip()
        return value or None


class WorkUpdateRequest(BaseModel):
    """Partial update — fields not provided are preserved. Publication is a
    separate explicit action (`/publish` / `/unpublish`) so an autosave can
    never accidentally publish a work."""

    model_config = ConfigDict(extra="forbid")

    title: str | None = Field(default=None, max_length=MAX_TITLE_LENGTH)
    summary: str | None = Field(default=None, max_length=MAX_SUMMARY_LENGTH)
    cover_media_id: str | None = None
    tags: list[str] | None = None
    external_links: list[ExternalLink] | None = None
    content: ContentDocument | None = None
    visibility: WorkVisibility | None = None

    @field_validator("title")
    @classmethod
    def _title(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return _title(value)

    @field_validator("summary")
    @classmethod
    def _summary(cls, value: str | None) -> str | None:
        return _optional_summary(value)

    @field_validator("tags")
    @classmethod
    def _tags(cls, value: list[str] | None) -> list[str] | None:
        if value is None:
            return None
        return _tag_list(value)

    @field_validator("cover_media_id")
    @classmethod
    def _media_id(cls, value: str | None) -> str | None:
        if value is None:
            return None
        value = value.strip()
        return value or None


# --------------------------------------------------------------------------
# Responses
# --------------------------------------------------------------------------
class WorkCertificationSummary(BaseModel):
    """Per-work certification state shown to the owner (and to reviewers in
    admin contexts). `changed_since_review` is derived from the frozen snapshot
    version vs the work's current version — never silently cleared."""

    model_config = ConfigDict(extra="forbid")

    request_id: str
    status: str
    version_reviewed: int
    reviewed_at: datetime | None
    feedback: str | None
    changed_since_review: bool
    reviewable: bool


class WorkCertificationRef(BaseModel):
    model_config = ConfigDict(extra="forbid")

    request_id: str | None = None
    status: str | None = None
    version_reviewed: int | None = None
    reviewed_at: datetime | None = None
    feedback: str | None = None
    changed_since_review: bool = False
    reviewable: bool = False


class WorkResponse(BaseModel):
    """Full member-owned view of a work (the owner always sees their own)."""

    model_config = ConfigDict(extra="forbid")

    id: str
    member_id: str
    title: str
    slug: str
    summary: str
    cover_media_id: str | None
    tags: list[str]
    external_links: list[ExternalLink]
    content: ContentDocument
    visibility: WorkVisibility
    publication_status: WorkPublicationStatus
    version: int
    profile_visibility: ProfileVisibility
    certification: WorkCertificationRef
    submitted_at: datetime | None
    review_feedback: str | None
    reviewed_at: datetime | None
    featured_on_projects: bool
    featured_classification: ProjectType | None
    featured_at: datetime | None
    created_at: datetime
    updated_at: datetime
    published_at: datetime | None

    @classmethod
    def from_work(
        cls,
        work: MemberWork,
        *,
        profile_visibility: ProfileVisibility,
        certification: WorkCertificationRef,
    ) -> "WorkResponse":
        return cls(
            id=work.id,
            member_id=work.member_id,
            title=work.title,
            slug=work.slug,
            summary=work.summary,
            cover_media_id=work.cover_media_id,
            tags=work.tags,
            external_links=work.external_links,
            content=work.content,
            visibility=work.visibility,
            publication_status=work.publication_status,
            version=work.version,
            profile_visibility=profile_visibility,
            certification=certification,
            submitted_at=work.submitted_at,
            review_feedback=work.review_feedback,
            reviewed_at=work.reviewed_at,
            featured_on_projects=work.featured_on_projects,
            featured_classification=work.featured_classification,
            featured_at=work.featured_at,
            created_at=work.created_at,
            updated_at=work.updated_at,
            published_at=work.published_at,
        )


class WorkCardResponse(BaseModel):
    """List item — excludes the content document (kept light)."""

    model_config = ConfigDict(extra="forbid")

    id: str
    member_id: str
    title: str
    slug: str
    summary: str
    cover_media_id: str | None
    tags: list[str]
    visibility: WorkVisibility
    publication_status: WorkPublicationStatus
    version: int
    certification: WorkCertificationRef
    submitted_at: datetime | None
    review_feedback: str | None
    reviewed_at: datetime | None
    featured_on_projects: bool
    featured_classification: ProjectType | None
    created_at: datetime
    updated_at: datetime
    published_at: datetime | None

    @classmethod
    def from_work(
        cls,
        work: MemberWork,
        *,
        certification: WorkCertificationRef,
    ) -> "WorkCardResponse":
        return cls(
            id=work.id,
            member_id=work.member_id,
            title=work.title,
            slug=work.slug,
            summary=work.summary,
            cover_media_id=work.cover_media_id,
            tags=work.tags,
            visibility=work.visibility,
            publication_status=work.publication_status,
            version=work.version,
            certification=certification,
            submitted_at=work.submitted_at,
            review_feedback=work.review_feedback,
            reviewed_at=work.reviewed_at,
            featured_on_projects=work.featured_on_projects,
            featured_classification=work.featured_classification,
            created_at=work.created_at,
            updated_at=work.updated_at,
            published_at=work.published_at,
        )


class WorkListResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    items: list[WorkCardResponse]
    total: int
    page: int
    page_size: int
    pages: int


# --------------------------------------------------------------------------
# Publication review (admin) + official featuring
# --------------------------------------------------------------------------
class WorkReviewDecisionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    action: Literal["approve", "request_changes", "reject"]
    feedback: str | None = Field(default=None, max_length=MAX_FEEDBACK_LENGTH)

    def clean_feedback(self) -> str | None:
        if self.feedback is None:
            return None
        cleaned = self.feedback.strip()
        return cleaned or None


class WorkFeatureRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    featured: bool
    classification: ProjectType | None = None


class AdminWorkCardResponse(BaseModel):
    """Admin queue/list view of any member work (subject to review/featuring)."""

    model_config = ConfigDict(extra="forbid")

    id: str
    member_id: str
    member_name: str
    title: str
    slug: str
    summary: str
    cover_media_id: str | None
    tags: list[str]
    visibility: WorkVisibility
    publication_status: WorkPublicationStatus
    version: int
    submitted_at: datetime | None
    review_feedback: str | None
    reviewed_at: datetime | None
    featured_on_projects: bool
    featured_classification: ProjectType | None
    featured_at: datetime | None
    published_at: datetime | None
    created_at: datetime
    updated_at: datetime

    @classmethod
    def from_work(cls, work: MemberWork, *, member_name: str) -> "AdminWorkCardResponse":
        return cls(
            id=work.id,
            member_id=work.member_id,
            member_name=member_name,
            title=work.title,
            slug=work.slug,
            summary=work.summary,
            cover_media_id=work.cover_media_id,
            tags=work.tags,
            visibility=work.visibility,
            publication_status=work.publication_status,
            version=work.version,
            submitted_at=work.submitted_at,
            review_feedback=work.review_feedback,
            reviewed_at=work.reviewed_at,
            featured_on_projects=work.featured_on_projects,
            featured_classification=work.featured_classification,
            featured_at=work.featured_at,
            published_at=work.published_at,
            created_at=work.created_at,
            updated_at=work.updated_at,
        )


class AdminWorkDetailResponse(AdminWorkCardResponse):
    external_links: list[ExternalLink]
    content: ContentDocument

    @classmethod
    def from_work(cls, work: MemberWork, *, member_name: str) -> "AdminWorkDetailResponse":
        base = AdminWorkCardResponse.from_work(work, member_name=member_name)
        return cls(
            **base.model_dump(),
            external_links=work.external_links,
            content=work.content,
        )


class AdminWorkListResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    items: list[AdminWorkCardResponse]
    total: int
    page: int
    page_size: int
    pages: int


# --------------------------------------------------------------------------
# Public surfaces
# --------------------------------------------------------------------------
class WorkPublicAuthor(BaseModel):
    model_config = ConfigDict(extra="forbid")

    member_id: str
    display_name: str
    picture_media_id: str | None


class WorkPublicResponse(BaseModel):
    """Public work page — published + public-visible works only."""

    model_config = ConfigDict(extra="forbid")

    slug: str
    title: str
    summary: str
    cover_media_id: str | None
    tags: list[str]
    external_links: list[ExternalLink]
    content: ContentDocument
    author: WorkPublicAuthor
    published_at: datetime
    updated_at: datetime


class WorkPublicCard(BaseModel):
    """A published, public-visible work as shown on a public member profile."""

    model_config = ConfigDict(extra="forbid")

    slug: str
    title: str
    summary: str
    cover_media_id: str | None
    tags: list[str]
    published_at: datetime


class WorkPublicList(BaseModel):
    model_config = ConfigDict(extra="forbid")

    items: list[WorkPublicCard]


class FeaturedContributionAuthor(BaseModel):
    model_config = ConfigDict(extra="forbid")

    member_id: str
    display_name: str
    picture_media_id: str | None


class FeaturedContributionCard(BaseModel):
    """A featured member work surfaced on the official Projects page.

    Eligibility is the ordinary composite public rule (published + public work
    AND active member with a public profile); featuring only adds curation.
    """

    model_config = ConfigDict(extra="forbid")

    slug: str
    title: str
    summary: str
    cover_media_id: str | None
    tags: list[str]
    classification: ProjectType
    featured_at: datetime | None
    published_at: datetime | None
    author: FeaturedContributionAuthor


class FeaturedContributionList(BaseModel):
    model_config = ConfigDict(extra="forbid")

    items: list[FeaturedContributionCard]


def require_work_owned(work: MemberWork, member_id: str) -> None:
    """Guard identity: a work belongs to exactly one member."""
    if work.member_id != member_id:
        raise AppError(404, "WORK_NOT_FOUND", "Work was not found")


def resolve_publication_target(action: Literal["publish", "unpublish"]) -> WorkPublicationStatus:
    return WorkPublicationStatus.PUBLISHED if action == "publish" else WorkPublicationStatus.UNPUBLISHED