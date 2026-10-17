"""Activity domain model.

Activities are the Phase 1 umbrella for three related-but-distinct offerings:

- **Project**      — invitation-only. An admin selects members, assigns each a
  role and sends invitation emails; invitations move through
  `invited → interested/declined → confirmed` and only confirmed participants
  count as active project members. Sending an invitation never adds a member.
- **Programme**    — open participation. Any eligible authenticated member may
  self-register; duplicates are prevented at the database level.
- **Hackathon**    — open participation, same self-registration rules.

Publishing/visibility is enforced server-side: only `published` activities are
ever visible through the public APIs; drafts are never exposed; cancelled and
archived activities are clearly marked and never promoted. Presentation labels
("Upcoming", "Ongoing", "Completed", "Cancelled") are *derived* from the stored
status plus the activity dates — the stored lifecycle is the source of truth.
"""

from __future__ import annotations

from datetime import date, datetime
from enum import Enum

from pydantic import BaseModel, ConfigDict, Field


class ActivityType(str, Enum):
    PROJECT = "project"
    PROGRAMME = "programme"
    HACKATHON = "hackathon"


class ActivityStatus(str, Enum):
    """Admin-controlled lifecycle. Draft is never public; cancelled and
    archived are terminal-ish states that are clearly marked publicly."""

    DRAFT = "draft"
    PUBLISHED = "published"
    CANCELLED = "cancelled"
    ARCHIVED = "archived"


class ParticipationStatus(str, Enum):
    """Participation lifecycle (shared by invitation and open registration).

    - `invited`    — a project invitation was sent, awaiting a reply.
    - `interested` — a positive reply was recorded by an admin (not yet
      confirmed).
    - `declined`   — the member declined (or an admin recorded a decline).
    - `confirmed`  — an active participant. Open self-registration starts here.
    - `withdrawn`  — the member withdrew (or was removed by an admin).

    Only `confirmed` participants are counted as active.
    """

    INVITED = "invited"
    INTERESTED = "interested"
    DECLINED = "declined"
    CONFIRMED = "confirmed"
    WITHDRAWN = "withdrawn"


class ParticipationSource(str, Enum):
    INVITED = "invited"
    SELF_REGISTERED = "self_registered"


class ActivityPresentationStatus(str, Enum):
    """Derived, public-facing label (never persisted as the source of truth)."""

    UPCOMING = "upcoming"
    ONGOING = "ongoing"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    ARCHIVED = "archived"


class ActivityBriefVersion(BaseModel):
    """One immutable revision of an activity's PDF brief.

    Replacing a brief never overwrites the previous object: a new version is
    appended, so the obligation an accepted participant agreed to remains
    auditable. Only the newest version is served publicly.
    """

    model_config = ConfigDict(extra="forbid")

    version: int
    object_key: str
    filename: str
    size_bytes: int
    checksum: str  # SHA-256 of the stored bytes
    mime_type: str = "application/pdf"
    uploaded_by: str  # admin id
    uploaded_at: datetime


class Activity(BaseModel):
    """Internal activity representation. Never serialised directly — response
    schemas live in the activities module."""

    model_config = ConfigDict(extra="forbid")

    id: str
    title: str
    slug: str
    activity_type: ActivityType
    summary: str = ""
    description: str = ""
    status: ActivityStatus = ActivityStatus.DRAFT
    start_date: date | None = None
    end_date: date | None = None
    banner_media_id: str | None = None
    featured: bool = False
    display_order: int = 0
    roles_offered: list[str] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)
    # Current brief (convenience pointer) plus the full append-only history.
    brief: ActivityBriefVersion | None = None
    brief_versions: list[ActivityBriefVersion] = Field(default_factory=list)
    cancel_reason: str | None = None
    created_by: str  # admin id
    created_at: datetime
    updated_at: datetime
    published_at: datetime | None = None
    cancelled_at: datetime | None = None
    archived_at: datetime | None = None

    @property
    def is_open_registration(self) -> bool:
        """Programme/Hackathon accept self-registration; Projects do not."""
        return self.activity_type in (ActivityType.PROGRAMME, ActivityType.HACKATHON)

    def registration_open(self, *, today: date) -> bool:
        """Whether self-registration is currently permitted."""
        if not self.is_open_registration or self.status != ActivityStatus.PUBLISHED:
            return False
        if self.end_date is not None and today > self.end_date:
            return False
        return True

    def presentation_status(self, *, today: date) -> ActivityPresentationStatus:
        """Derive the public label from the stored lifecycle + dates."""
        if self.status == ActivityStatus.CANCELLED:
            return ActivityPresentationStatus.CANCELLED
        if self.status == ActivityStatus.ARCHIVED:
            return ActivityPresentationStatus.ARCHIVED
        # Draft is never public; label it Upcoming for any internal preview.
        if self.status == ActivityStatus.DRAFT:
            return ActivityPresentationStatus.UPCOMING
        if self.end_date is not None and today > self.end_date:
            return ActivityPresentationStatus.COMPLETED
        if self.start_date is not None and today >= self.start_date:
            return ActivityPresentationStatus.ONGOING
        return ActivityPresentationStatus.UPCOMING


class ActivityParticipation(BaseModel):
    """A single member's participation in one activity.

    Exactly one record exists per (activity, member) — enforced by a unique
    index — which is what makes open self-registration duplicate-safe.
    """

    model_config = ConfigDict(extra="forbid")

    id: str
    activity_id: str
    member_id: str  # internal Mongo id of the member
    member_readable_id: str  # THL-M-YYYY-NNNN (display + stable reference)
    role: str | None = None  # assigned role (project invitations)
    status: ParticipationStatus = ParticipationStatus.INVITED
    source: ParticipationSource = ParticipationSource.INVITED
    note: str | None = None  # admin-only note
    invited_at: datetime | None = None
    responded_at: datetime | None = None
    confirmed_at: datetime | None = None
    withdrawn_at: datetime | None = None
    email_sent_at: datetime | None = None
    created_at: datetime
    updated_at: datetime
