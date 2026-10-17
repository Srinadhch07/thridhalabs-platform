"""Pydantic schemas for the member accounts API (member + admin surfaces).

API boundaries expose clean models only: never raw MongoDB documents, never
password hashes or onboarding tokens — those never cross the API boundary.
"""

from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

from app.core.validators import non_empty_name, optional_http_url
from app.models.member import Member, MemberStatus, ProfileVisibility

MAX_NAME_LENGTH = 200
MAX_BIO_LENGTH = 2000
MAX_TAG_LENGTH = 100
MAX_TAGS = 50
MAX_LABEL_LENGTH = 80
MAX_NOTE_LENGTH = 2000


def _tag_list(value: list[str]) -> list[str]:
    cleaned: list[str] = []
    for entry in value:
        item = entry.strip()
        if not item:
            continue
        if len(item) > MAX_TAG_LENGTH:
            raise ValueError(
                f"Each tag must be at most {MAX_TAG_LENGTH} characters"
            )
        cleaned.append(item)
    if len(cleaned) > MAX_TAGS:
        raise ValueError(f"At most {MAX_TAGS} tags are allowed")
    return cleaned


def _timezone(value: str | None) -> str | None:
    if value is None:
        return None
    value = value.strip()
    if not value:
        return None
    try:
        ZoneInfo(value)
    except (ZoneInfoNotFoundError, ValueError) as exc:
        raise ValueError("Must be a valid IANA timezone") from exc
    return value


# --------------------------------------------------------------------------
# Member-facing (self-service) schemas
# --------------------------------------------------------------------------
class MemberSetupRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    token: str = Field(min_length=8, max_length=256)
    # Strength is enforced by the shared password policy at creation.
    password: str = Field(min_length=1, max_length=256)


class MemberLoginRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    email: EmailStr
    password: str = Field(min_length=1, max_length=256)


class MemberPasswordChangeRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    current_password: str = Field(min_length=1, max_length=256)
    new_password: str = Field(min_length=1, max_length=256)


class MemberProfileUpdate(BaseModel):
    """Full replacement of the member-managed profile fields."""

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
    # Omitted (`None`) keeps the current visibility; an explicit value sets it.
    profile_visibility: ProfileVisibility | None = None

    @field_validator("display_name")
    @classmethod
    def _display_name(cls, value: str | None) -> str | None:
        if value is None:
            return None
        value = value.strip()
        if len(value) > MAX_NAME_LENGTH:
            raise ValueError(f"Must be at most {MAX_NAME_LENGTH} characters")
        return value or None

    @field_validator("bio", "location")
    @classmethod
    def _length_limited(cls, value: str | None) -> str | None:
        if value is None:
            return None
        value = value.strip()
        if len(value) > MAX_BIO_LENGTH:
            raise ValueError(f"Must be at most {MAX_BIO_LENGTH} characters")
        return value or None

    @field_validator("skills", "interests")
    @classmethod
    def _tags(cls, value: list[str]) -> list[str]:
        return _tag_list(value)

    @field_validator("github_url", "linkedin_url", "portfolio_url")
    @classmethod
    def _url(cls, value: str | None) -> str | None:
        return optional_http_url(value)

    @field_validator("timezone")
    @classmethod
    def _tz(cls, value: str | None) -> str | None:
        return _timezone(value)


class MemberProfileInfo(BaseModel):
    model_config = ConfigDict(extra="forbid")

    display_name: str | None
    bio: str | None
    skills: list[str]
    interests: list[str]
    github_url: str | None
    linkedin_url: str | None
    portfolio_url: str | None
    location: str | None
    timezone: str | None
    picture_media_id: str | None
    profile_visibility: ProfileVisibility
    completed_at: datetime | None

    @classmethod
    def from_member(cls, member: Member) -> "MemberProfileInfo":
        profile = member.profile
        return cls(
            display_name=profile.display_name,
            bio=profile.bio,
            skills=profile.skills,
            interests=profile.interests,
            github_url=profile.github_url,
            linkedin_url=profile.linkedin_url,
            portfolio_url=profile.portfolio_url,
            location=profile.location,
            timezone=profile.timezone,
            picture_media_id=profile.picture_media_id,
            profile_visibility=profile.profile_visibility,
            completed_at=profile.completed_at,
        )


class MemberMeResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    member_id: str
    email: str
    status: MemberStatus
    full_name: str | None
    profile_complete: bool
    last_login_at: datetime | None


class MemberProfileResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    member_id: str
    email: str
    status: MemberStatus
    full_name: str | None
    role_label: str | None
    profile: MemberProfileInfo
    profile_complete: bool
    created_at: datetime

    @classmethod
    def from_member(cls, member: Member) -> "MemberProfileResponse":
        return cls(
            id=member.id,
            member_id=member.member_id,
            email=member.email,
            status=member.status,
            full_name=member.full_name,
            role_label=member.role_label,
            profile=MemberProfileInfo.from_member(member),
            profile_complete=member.profile_complete,
            created_at=member.created_at,
        )


# --------------------------------------------------------------------------
# Admin-only schemas
# --------------------------------------------------------------------------
class MemberCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    email: EmailStr
    full_name: str | None = None
    role_label: str | None = None
    joined_opportunity_id: str | None = None
    internal_note: str | None = None

    @field_validator("full_name")
    @classmethod
    def _full_name(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return non_empty_name(value, max_length=MAX_NAME_LENGTH)

    @field_validator("role_label")
    @classmethod
    def _role_label(cls, value: str | None) -> str | None:
        if value is None:
            return None
        value = value.strip()
        if not value:
            return None
        if len(value) > MAX_LABEL_LENGTH:
            raise ValueError(f"Must be at most {MAX_LABEL_LENGTH} characters")
        return value

    @field_validator("internal_note")
    @classmethod
    def _note(cls, value: str | None) -> str | None:
        if value is None:
            return None
        value = value.strip()
        if len(value) > MAX_NOTE_LENGTH:
            raise ValueError(f"Must be at most {MAX_NOTE_LENGTH} characters")
        return value or None


class MemberUpdateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    email: EmailStr | None = None
    full_name: str | None = None
    role_label: str | None = None
    joined_opportunity_id: str | None = None
    internal_note: str | None = None

    @field_validator("full_name")
    @classmethod
    def _full_name(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return non_empty_name(value, max_length=MAX_NAME_LENGTH)

    @field_validator("role_label")
    @classmethod
    def _role_label(cls, value: str | None) -> str | None:
        if value is None:
            return None
        value = value.strip()
        if not value:
            return None
        if len(value) > MAX_LABEL_LENGTH:
            raise ValueError(f"Must be at most {MAX_LABEL_LENGTH} characters")
        return value

    @field_validator("internal_note")
    @classmethod
    def _note(cls, value: str | None) -> str | None:
        if value is None:
            return None
        value = value.strip()
        if len(value) > MAX_NOTE_LENGTH:
            raise ValueError(f"Must be at most {MAX_NOTE_LENGTH} characters")
        return value or None


class MemberAdminResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    member_id: str
    email: str
    status: MemberStatus
    full_name: str | None
    role_label: str | None
    joined_opportunity_id: str | None
    internal_note: str | None
    profile: MemberProfileInfo
    profile_complete: bool
    onboarding_sent: bool
    onboarding_completed_at: datetime | None
    created_by: str
    created_at: datetime
    updated_at: datetime
    last_login_at: datetime | None

    @classmethod
    def from_member(cls, member: Member) -> "MemberAdminResponse":
        return cls(
            id=member.id,
            member_id=member.member_id,
            email=member.email,
            status=member.status,
            full_name=member.full_name,
            role_label=member.role_label,
            joined_opportunity_id=member.joined_opportunity_id,
            internal_note=member.internal_note,
            profile=MemberProfileInfo.from_member(member),
            profile_complete=member.profile_complete,
            onboarding_sent=member.onboarding.sent_at is not None,
            onboarding_completed_at=member.onboarding.completed_at,
            created_by=member.created_by,
            created_at=member.created_at,
            updated_at=member.updated_at,
            last_login_at=member.last_login_at,
        )


class MemberListResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    items: list[MemberAdminResponse]
    total: int
    page: int
    page_size: int
    pages: int