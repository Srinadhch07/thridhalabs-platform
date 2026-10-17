"""Member account domain model (Lab Member Account System).

Members are provisioned by admins (no public registration). An account starts
in `pending_setup` with a single-use, hashed onboarding token; once the member
sets a password and completes the required profile fields, it becomes `active`.
`inactive` accounts are blocked from login, onboarding and session renewal.

Members are intentionally NOT admins: they live in their own collection, carry
their own JWT claim (`typ=member`) and can never reach admin routes. Member
`role_label` is a display attribute managed by admins, never a privilege.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, ConfigDict, Field


class MemberStatus(str, Enum):
    PENDING_SETUP = "pending_setup"
    ACTIVE = "active"
    INACTIVE = "inactive"


class ProfileVisibility(str, Enum):
    """Who can see the member's public profile and public works.

    A member's works can never be more visible than their profile: public
    works require a public profile, and `members`/`private` works are
    constrained by their own visibility regardless of this setting.
    """

    PRIVATE = "private"   # only the member (and admins) can see the profile
    MEMBERS = "members"   # any signed-in member can see the profile
    PUBLIC = "public"     # anyone can see the profile (and public works)


class MemberOnboarding(BaseModel):
    """Onboarding-token state. Only the SHA-256 hash is stored — never the
    plaintext token. A cleared `token_hash` means the token was consumed or
    invalidated (single-use)."""

    model_config = ConfigDict(extra="forbid")

    token_hash: str | None = None
    expires_at: datetime | None = None
    sent_at: datetime | None = None
    completed_at: datetime | None = None

    @property
    def pending(self) -> bool:
        """A live, unused onboarding link exists."""
        return self.token_hash is not None and self.completed_at is None


class MemberProfile(BaseModel):
    """Member-provided profile data. Only the member edits these fields;
    admins can read them. `completed_at` records the moment the required
    fields were first satisfied."""

    model_config = ConfigDict(extra="forbid")

    display_name: str | None = None
    bio: str | None = None
    skills: list[str] = Field(default_factory=list)
    interests: list[str] = Field(default_factory=list)
    github_url: str | None = None
    linkedin_url: str | None = None
    portfolio_url: str | None = None
    location: str | None = None
    timezone: str | None = None
    picture_media_id: str | None = None
    profile_visibility: ProfileVisibility = ProfileVisibility.PRIVATE
    completed_at: datetime | None = None

    def is_complete(self, *, full_name: str | None) -> bool:
        """Required profile-setup fields: full name, short bio, skills and
        interests (display name and picture are optional)."""
        return bool(full_name and self.bio and self.skills and self.interests)


class Member(BaseModel):
    """Internal member representation. Never serialised to API responses
    directly — response schemas live in the members module."""

    model_config = ConfigDict(extra="forbid")

    id: str
    member_id: str  # readable THL-M-YYYY-NNNN (permanent, never reused)
    email: str  # normalized lowercase
    password_hash: str | None = Field(default=None, repr=False)
    status: MemberStatus = MemberStatus.PENDING_SETUP
    token_version: int = 0
    # Admin-managed fields.
    full_name: str | None = None
    role_label: str | None = None
    joined_opportunity_id: str | None = None
    internal_note: str | None = None
    created_by: str  # admin id
    created_at: datetime
    updated_at: datetime
    last_login_at: datetime | None = None
    onboarding: MemberOnboarding = Field(default_factory=MemberOnboarding)
    profile: MemberProfile = Field(default_factory=MemberProfile)

    @property
    def profile_complete(self) -> bool:
        return self.profile.is_complete(full_name=self.full_name)