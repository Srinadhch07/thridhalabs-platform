"""Pydantic schemas for the AI summaries API (Admin only).

Expose the draft/published slots, the exact source reports (+ versions) used,
the generation history and a derived `state` for the UI. Internal review notes
and the (never-stored) API key are not part of this contract.
"""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models.ai_summary import (
    MAX_SUMMARY_LENGTH,
    AiSummary,
    SummaryGenerationEntry,
    SummarySource,
)

SummaryState = Literal["empty", "draft", "published", "outdated", "failed"]


# --------------------------------------------------------------------------
# Requests
# --------------------------------------------------------------------------
class SummaryGenerateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    activity_id: str = Field(min_length=1, max_length=200)
    member_id: str = Field(min_length=1, max_length=200)

    @field_validator("activity_id", "member_id")
    @classmethod
    def _trim(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Must not be empty")
        return value


class SummaryDraftSaveRequest(BaseModel):
    """Save (review) the editable draft. Saving does not publish anything."""

    model_config = ConfigDict(extra="forbid")

    draft_content: str = Field(max_length=MAX_SUMMARY_LENGTH)

    @field_validator("draft_content")
    @classmethod
    def _content(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Draft content must not be empty")
        return value


# --------------------------------------------------------------------------
# Responses
# --------------------------------------------------------------------------
class SummarySourceRef(BaseModel):
    model_config = ConfigDict(extra="forbid")

    report_id: str
    version: int
    submitted_at: datetime


class SummaryGenerationEntryResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    at: datetime
    model: str
    status: Literal["ok", "error"]
    error_code: str | None
    error_message: str | None

    @classmethod
    def from_entry(cls, entry: SummaryGenerationEntry) -> "SummaryGenerationEntryResponse":
        return cls(
            at=entry.at,
            model=entry.model,
            status=entry.status,
            error_code=entry.error_code,
            error_message=entry.error_message,
        )


class AiSummaryAdminResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    activity_id: str
    activity_slug: str
    activity_title: str
    member_id: str
    member_readable_id: str
    member_name: str
    state: SummaryState

    draft_content: str | None
    draft_model: str | None
    draft_generated_at: datetime | None
    draft_reviewed: bool
    draft_outdated: bool

    published_content: str | None
    published_model: str | None
    published_at: datetime | None

    source_reports: list[SummarySourceRef]
    source_report_count: int
    outdated: bool
    last_error_code: str | None
    last_error_message: str | None
    generations: list[SummaryGenerationEntryResponse]
    updated_at: datetime


class AiSummaryListResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    items: list[AiSummaryAdminResponse]
    total: int
    page: int
    page_size: int
    pages: int


# ---- Source / target overview -------------------------------------------
class AiSourceMemberOption(BaseModel):
    model_config = ConfigDict(extra="forbid")

    member_id: str
    member_readable_id: str
    member_name: str
    approved_count: int
    summary_id: str | None
    summary_state: SummaryState | None


class AiSourceProjectOption(BaseModel):
    model_config = ConfigDict(extra="forbid")

    activity_id: str
    slug: str
    title: str
    approved_count: int
    members: list[AiSourceMemberOption]


class AiSourceOverviewResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    projects: list[AiSourceProjectOption]


# ---- Public (unauthenticated) projection ---------------------------------
class PublicContributionSummary(BaseModel):
    """A published, Admin-reviewed AI contribution summary as shown on a
    member's **public** profile.

    Deliberately minimal: no internal ids, no member ids, no draft/unpublished
    fields, no review notes, no source report ids, no model/API settings. Only
    what is needed to display a verified contribution.
    """

    model_config = ConfigDict(extra="forbid")

    activity_title: str
    role: str | None
    content: str
    published_at: datetime
    source_report_count: int
    period_start: datetime | None
    period_end: datetime | None


def _source_refs(sources: list[SummarySource]) -> list[SummarySourceRef]:
    return [
        SummarySourceRef(
            report_id=src.report_id,
            version=src.version,
            submitted_at=src.submitted_at,
        )
        for src in sources
    ]


def derive_state(summary: AiSummary, current_hash: str | None) -> SummaryState:
    """Compute the UI state from the persisted slots + current source hash.

    - published and its sources changed  -> "outdated"
    - published                          -> "published"
    - a draft exists                     -> "draft"
    - last generation failed             -> "failed"
    - nothing yet                        -> "empty"
    """
    if summary.published_content:
        if current_hash is not None and summary.published_source_hash != current_hash:
            return "outdated"
        return "published"
    if summary.draft_content:
        return "draft"
    if summary.last_error_code:
        return "failed"
    return "empty"


def admin_response(
    summary: AiSummary,
    *,
    member_name: str,
    current_hash: str | None,
) -> AiSummaryAdminResponse:
    active_sources = (
        summary.draft_source_reports
        if summary.draft_content is not None
        else summary.published_source_reports
    )
    draft_outdated = bool(
        summary.draft_content
        and current_hash is not None
        and summary.draft_source_hash != current_hash
    )
    outdated = bool(
        summary.published_content
        and current_hash is not None
        and summary.published_source_hash != current_hash
    )
    return AiSummaryAdminResponse(
        id=summary.id,
        activity_id=summary.activity_id,
        activity_slug=summary.activity_slug,
        activity_title=summary.activity_title,
        member_id=summary.member_id,
        member_readable_id=summary.member_readable_id,
        member_name=member_name,
        state=derive_state(summary, current_hash),
        draft_content=summary.draft_content,
        draft_model=summary.draft_model,
        draft_generated_at=summary.draft_generated_at,
        draft_reviewed=summary.draft_reviewed_at is not None,
        draft_outdated=draft_outdated,
        published_content=summary.published_content,
        published_model=summary.published_model,
        published_at=summary.published_at,
        source_reports=_source_refs(active_sources),
        source_report_count=len(active_sources),
        outdated=outdated,
        last_error_code=summary.last_error_code,
        last_error_message=summary.last_error_message,
        generations=[
            SummaryGenerationEntryResponse.from_entry(entry)
            for entry in summary.generations
        ],
        updated_at=summary.updated_at,
    )
