"""Pydantic schemas for the Project Progress Reports API (member + admin).

API boundaries expose clean models only: never raw MongoDB documents, never the
author's internal Mongo `_id` in member-facing responses. Both surfaces validate
the 500-character description and evidence links (http/https only).
"""

from __future__ import annotations

from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.core.validators import optional_http_url
from app.models.activity import ActivityPresentationStatus
from app.models.progress_report import (
    MAX_DESCRIPTION_LENGTH,
    MAX_EVIDENCE_LINKS,
    MAX_FEEDBACK_LENGTH,
    MAX_URL_LENGTH,
    ProgressReport,
    ReportStatus,
)


def _description(value: str) -> str:
    value = value.strip()
    if not value:
        raise ValueError("Description is required")
    if len(value) > MAX_DESCRIPTION_LENGTH:
        raise ValueError(f"Must be at most {MAX_DESCRIPTION_LENGTH} characters")
    return value


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


# --------------------------------------------------------------------------
# Requests
# --------------------------------------------------------------------------
class ReportCreateRequest(BaseModel):
    """Submit a progress report. The author is always the authenticated member;
    `activity_id` must reference a project the member is a *confirmed*
    participant of (enforced server-side)."""

    model_config = ConfigDict(extra="forbid")

    activity_id: str = Field(min_length=1, max_length=200)
    description: str = Field(max_length=MAX_DESCRIPTION_LENGTH)
    evidence_links: list[str] = Field(default_factory=list, max_length=MAX_EVIDENCE_LINKS)
    # Optional idempotency key so a double-click/retry cannot create duplicates.
    client_request_id: str | None = Field(default=None, max_length=200)

    @field_validator("activity_id")
    @classmethod
    def _activity_id(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Project is required")
        return value

    @field_validator("description")
    @classmethod
    def _description(cls, value: str) -> str:
        return _description(value)

    @field_validator("evidence_links")
    @classmethod
    def _evidence_links(cls, value: list[str]) -> list[str]:
        return _evidence_links(value)

    @field_validator("client_request_id")
    @classmethod
    def _client_request_id(cls, value: str | None) -> str | None:
        if value is None:
            return None
        value = value.strip()
        return value or None


class ReportUpdateRequest(BaseModel):
    """Edit and resubmit a report while it is not yet finalised. The content is
    fully replaced; prior review history is retained by the service."""

    model_config = ConfigDict(extra="forbid")

    description: str = Field(max_length=MAX_DESCRIPTION_LENGTH)
    evidence_links: list[str] = Field(default_factory=list, max_length=MAX_EVIDENCE_LINKS)

    @field_validator("description")
    @classmethod
    def _description(cls, value: str) -> str:
        return _description(value)

    @field_validator("evidence_links")
    @classmethod
    def _evidence_links(cls, value: list[str]) -> list[str]:
        return _evidence_links(value)


class ReportDecisionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    action: Literal["approve", "request_changes"]
    feedback: str | None = Field(default=None, max_length=MAX_FEEDBACK_LENGTH)

    def clean_feedback(self) -> str | None:
        if self.feedback is None:
            return None
        cleaned = self.feedback.strip()
        return cleaned or None


# --------------------------------------------------------------------------
# Responses
# --------------------------------------------------------------------------
class ReportReviewEntryResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: ReportStatus
    reviewer_name: str | None
    feedback: str | None
    version: int
    decided_at: datetime

    @classmethod
    def from_entry(cls, entry) -> "ReportReviewEntryResponse":  # noqa: ANN001
        return cls(
            status=entry.status,
            reviewer_name=entry.reviewer_name,
            feedback=entry.feedback,
            version=entry.version,
            decided_at=entry.decided_at,
        )


class ReportResponse(BaseModel):
    """Member-facing view of one of the member's own reports."""

    model_config = ConfigDict(extra="forbid")

    id: str
    activity_id: str
    activity_slug: str
    activity_title: str
    role: str | None
    description: str
    evidence_links: list[str]
    status: ReportStatus
    version: int
    editable: bool
    submitted_at: datetime
    updated_at: datetime
    reviewed_at: datetime | None
    review_feedback: str | None
    review_history: list[ReportReviewEntryResponse]

    @classmethod
    def from_report(cls, report: ProgressReport) -> "ReportResponse":
        return cls(
            id=report.id,
            activity_id=report.activity_id,
            activity_slug=report.activity_slug,
            activity_title=report.activity_title,
            role=report.role,
            description=report.description,
            evidence_links=report.evidence_links,
            status=report.status,
            version=report.version,
            editable=report.status != ReportStatus.APPROVED,
            submitted_at=report.submitted_at,
            updated_at=report.updated_at,
            reviewed_at=report.reviewed_at,
            review_feedback=report.review_feedback,
            review_history=[
                ReportReviewEntryResponse.from_entry(entry)
                for entry in report.review_history
            ],
        )


class ReportListResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    items: list[ReportResponse]
    total: int
    page: int
    page_size: int
    pages: int


# ---- Member projects overview -------------------------------------------
class MemberProjectSummary(BaseModel):
    """A project the member is a confirmed participant of, with a roll-up of
    their report state (used by the member portal's "My Projects")."""

    model_config = ConfigDict(extra="forbid")

    activity_id: str
    slug: str
    title: str
    role: str | None
    presentation_status: ActivityPresentationStatus
    start_date: date | None
    end_date: date | None
    banner_media_id: str | None
    report_count: int = 0
    pending_count: int = 0
    changes_requested_count: int = 0
    approved_count: int = 0
    last_report_at: datetime | None = None


class MemberProjectListResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    items: list[MemberProjectSummary]


# ---- Contribution history -----------------------------------------------
class ContributionReportResponse(BaseModel):
    """One approved report as it appears in the member's official contribution
    history (grouped by project). Only approved reports are ever included."""

    model_config = ConfigDict(extra="forbid")

    id: str
    description: str
    evidence_links: list[str]
    approved_at: datetime
    submitted_at: datetime


class ContributionSummaryResponse(BaseModel):
    """One *published* AI work summary, as it appears in the member's official
    contribution history. Drafts are never included; internal review notes and
    source API settings are never exposed."""

    model_config = ConfigDict(extra="forbid")

    id: str
    content: str
    model: str | None
    published_at: datetime
    source_report_count: int
    source_report_ids: list[str]


class ContributionProjectGroup(BaseModel):
    model_config = ConfigDict(extra="forbid")

    activity_id: str
    slug: str
    title: str
    role: str | None
    report_count: int
    reports: list[ContributionReportResponse]
    summaries: list[ContributionSummaryResponse] = Field(default_factory=list)


class ContributionHistoryResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    items: list[ContributionProjectGroup]
    total_reports: int


# ---- Admin ---------------------------------------------------------------
class AdminReportResponse(BaseModel):
    """Admin view of any report (review queue + detail)."""

    model_config = ConfigDict(extra="forbid")

    id: str
    activity_id: str
    activity_slug: str
    activity_title: str
    member_id: str
    member_readable_id: str
    member_name: str
    member_email: str | None
    role: str | None
    description: str
    evidence_links: list[str]
    status: ReportStatus
    version: int
    submitted_at: datetime
    updated_at: datetime
    reviewed_at: datetime | None
    reviewed_by: str | None
    review_feedback: str | None
    review_history: list[ReportReviewEntryResponse]

    @classmethod
    def from_report(
        cls,
        report: ProgressReport,
        *,
        member_name: str,
        member_email: str | None,
    ) -> "AdminReportResponse":
        return cls(
            id=report.id,
            activity_id=report.activity_id,
            activity_slug=report.activity_slug,
            activity_title=report.activity_title,
            member_id=report.member_id,
            member_readable_id=report.member_readable_id,
            member_name=member_name,
            member_email=member_email,
            role=report.role,
            description=report.description,
            evidence_links=report.evidence_links,
            status=report.status,
            version=report.version,
            submitted_at=report.submitted_at,
            updated_at=report.updated_at,
            reviewed_at=report.reviewed_at,
            reviewed_by=report.reviewed_by,
            review_feedback=report.review_feedback,
            review_history=[
                ReportReviewEntryResponse.from_entry(entry)
                for entry in report.review_history
            ],
        )


class AdminReportListResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    items: list[AdminReportResponse]
    total: int
    page: int
    page_size: int
    pages: int


__all__ = [
    "MAX_URL_LENGTH",
    "AdminReportListResponse",
    "AdminReportResponse",
    "ContributionHistoryResponse",
    "ContributionProjectGroup",
    "ContributionReportResponse",
    "ContributionSummaryResponse",
    "MemberProjectListResponse",
    "MemberProjectSummary",
    "ReportCreateRequest",
    "ReportDecisionRequest",
    "ReportListResponse",
    "ReportResponse",
    "ReportUpdateRequest",
]
