"""AI work-summary domain model (Groq-generated, admin-reviewed drafts).

A summary aggregates the **approved** progress reports for one (project, member)
pair into an editable narrative. Generation, review and publication are distinct,
explicit Admin actions — a summary only becomes part of official contribution
history when an Admin explicitly *publishes* it.

At most one summary document exists per (project, member) — enforced by a unique
index. The document holds two independent slots:

- a **draft** slot (`draft_*`): the latest generated/edited, not-yet-official
  text, its source report ids + content versions, and whether it has been
  reviewed (saved);
- a **published** slot (`published_*`): the current official text.

Generating or saving a draft never mutates the published slot, so a failed or
in-progress generation cannot damage the published summary. Replacing a
published summary archives the previous version into a bounded
`publication_history` trail.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

MAX_SUMMARY_LENGTH = 20_000
MAX_PUBLICATION_HISTORY = 20
MAX_GENERATION_HISTORY = 20


class SummaryStatus(str, Enum):
    """Persisted official state of a summary record."""

    DRAFT = "draft"
    PUBLISHED = "published"


class SummarySource(BaseModel):
    """One source report pinned to the exact content version that was used."""

    model_config = ConfigDict(extra="forbid")

    report_id: str
    version: int
    submitted_at: datetime


class SummaryGenerationEntry(BaseModel):
    """One generation attempt (append-only audit trail, bounded in length)."""

    model_config = ConfigDict(extra="forbid")

    at: datetime
    by: str  # admin id
    model: str
    status: Literal["ok", "error"]
    source_hash: str | None = None
    error_code: str | None = None
    error_message: str | None = None


class AiSummary(BaseModel):
    """Internal summary representation. Never serialised directly — response
    schemas live in the ai module's `schemas` module."""

    model_config = ConfigDict(extra="forbid")

    id: str
    activity_id: str
    activity_slug: str
    activity_title: str
    member_id: str
    member_readable_id: str
    status: SummaryStatus = SummaryStatus.DRAFT

    # --- draft slot (not official) ---
    draft_content: str | None = None
    draft_model: str | None = None
    draft_source_hash: str | None = None
    draft_source_reports: list[SummarySource] = Field(default_factory=list)
    draft_generated_at: datetime | None = None
    draft_generated_by: str | None = None
    draft_reviewed_at: datetime | None = None

    # --- published slot (official contribution history) ---
    published_content: str | None = None
    published_model: str | None = None
    published_source_hash: str | None = None
    published_source_reports: list[SummarySource] = Field(default_factory=list)
    published_at: datetime | None = None
    published_by: str | None = None

    publication_history: list[dict] = Field(default_factory=list)
    generations: list[SummaryGenerationEntry] = Field(default_factory=list)
    last_error_code: str | None = None
    last_error_message: str | None = None

    created_at: datetime
    updated_at: datetime
