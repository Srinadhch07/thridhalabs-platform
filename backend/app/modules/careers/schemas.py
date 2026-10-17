"""Pydantic schemas for the careers API (admin + public).

Public responses never expose drafts/closed opportunities (enforced in the
service) and never leak internal Mongo ids, admin metadata or the owner's
admin-only email configuration. Only the fields required to render the public
careers page and build the email apply link are returned.
"""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.core.validators import non_empty_name, optional_email
from app.models.careers import (
    CareersSettings,
    Opportunity,
    OpportunityStatus,
    OpportunityType,
    WorkMode,
)

MAX_TITLE_LENGTH = 200
MAX_TEXT_LENGTH = 2000
MAX_HEADING_LENGTH = 200
MAX_CUSTOM_TYPE_LENGTH = 100
MAX_SKILLS = 30
MAX_SKILL_LENGTH = 40


def _list_of_strings(value: list[str], max_items: int, item_max: int) -> list[str]:
    cleaned = [item.strip()[:item_max] for item in value if item.strip()]
    return list(dict.fromkeys(cleaned))[:max_items]


# --------------------------------------------------------------------------
# Settings
# --------------------------------------------------------------------------
class CareersSettingsUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    enabled: bool | None = None
    heading: str | None = Field(default=None, max_length=MAX_HEADING_LENGTH)
    description: str | None = Field(default=None, max_length=MAX_TEXT_LENGTH)
    application_email: str | None = None
    application_template: str | None = Field(default=None, max_length=MAX_TEXT_LENGTH)

    @field_validator("application_email")
    @classmethod
    def _email(cls, value: str | None) -> str | None:
        return optional_email(value)


# --------------------------------------------------------------------------
# Opportunities
# --------------------------------------------------------------------------
class OpportunityCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str
    slug: str | None = None
    type: OpportunityType
    custom_type: str | None = Field(default=None, max_length=MAX_CUSTOM_TYPE_LENGTH)
    description: str = Field(..., max_length=MAX_TEXT_LENGTH)
    skills: list[str] = Field(default_factory=list)
    work_mode: WorkMode | None = None
    application_email: str | None = None
    status: OpportunityStatus = OpportunityStatus.DRAFT
    display_order: int = Field(default=0, ge=0)

    @field_validator("title")
    @classmethod
    def _title(cls, value: str) -> str:
        return non_empty_name(value, max_length=MAX_TITLE_LENGTH)

    @field_validator("skills")
    @classmethod
    def _skills(cls, value: list[str]) -> list[str]:
        return _list_of_strings(value, MAX_SKILLS, MAX_SKILL_LENGTH)

    @field_validator("application_email")
    @classmethod
    def _email(cls, value: str | None) -> str | None:
        return optional_email(value)

    @field_validator("custom_type")
    @classmethod
    def _custom_type(cls, value: str | None) -> str | None:
        if value is None:
            return None
        value = value.strip()
        return value or None

    @model_validator(mode="after")
    def _coerce_custom_type(self) -> "OpportunityCreate":
        if self.type == OpportunityType.OTHER:
            if not self.custom_type:
                raise ValueError("A custom type label is required when type is Other")
        else:
            self.custom_type = None
        return self


class OpportunityUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str | None = None
    slug: str | None = None
    type: OpportunityType | None = None
    custom_type: str | None = Field(default=None, max_length=MAX_CUSTOM_TYPE_LENGTH)
    description: str | None = Field(default=None, max_length=MAX_TEXT_LENGTH)
    skills: list[str] | None = None
    work_mode: WorkMode | None = None
    application_email: str | None = None
    status: OpportunityStatus | None = None
    display_order: int | None = Field(default=None, ge=0)

    @field_validator("title")
    @classmethod
    def _title(cls, value: str | None) -> str | None:
        return non_empty_name(value, max_length=MAX_TITLE_LENGTH) if value is not None else None

    @field_validator("skills")
    @classmethod
    def _skills(cls, value: list[str] | None) -> list[str] | None:
        if value is None:
            return None
        return _list_of_strings(value, MAX_SKILLS, MAX_SKILL_LENGTH)

    @field_validator("application_email")
    @classmethod
    def _email(cls, value: str | None) -> str | None:
        return optional_email(value)

    @field_validator("custom_type")
    @classmethod
    def _custom_type(cls, value: str | None) -> str | None:
        if value is None:
            return None
        value = value.strip()
        return value or None

    @model_validator(mode="after")
    def _coerce_custom_type(self) -> "OpportunityUpdate":
        if self.type == OpportunityType.OTHER:
            if not self.custom_type:
                raise ValueError("A custom type label is required when type is Other")
        elif self.custom_type is not None and self.type is not None:
            self.custom_type = None
        return self


# --------------------------------------------------------------------------
# Responses
# --------------------------------------------------------------------------
class CareersSettingsAdminResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    enabled: bool
    heading: str
    description: str
    application_email: str | None
    application_template: str | None
    created_at: datetime
    updated_at: datetime


class CareersSettingsPublicResponse(BaseModel):
    """Safe public subset (presentation + apply template only).

    `enabled` is a public boolean by design (like `maintenance_mode` in site
    settings) — the public navigation cannot hide/show Careers without it. When
    careers are disabled only that flag is meaningful; heading/description and
    the application template default to null.
    """

    model_config = ConfigDict(extra="forbid")

    enabled: bool
    heading: str | None
    description: str | None
    application_template: str | None


class OpportunityAdminResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    title: str
    slug: str
    type: OpportunityType
    custom_type: str | None
    description: str
    skills: list[str]
    work_mode: WorkMode | None
    application_email: str | None
    status: OpportunityStatus
    display_order: int
    created_at: datetime
    updated_at: datetime


class OpportunityPublicResponse(BaseModel):
    """Public opportunity — render + apply-link fields only, no Mongo id.

    `application_email` is the RESOLVED address (per-opportunity override else
    the global default) so the public site never mixes sources; it is null when
    no address is configured, which the frontend treats as a fallback state.
    """

    model_config = ConfigDict(extra="forbid")

    slug: str
    title: str
    type: OpportunityType
    custom_type: str | None
    description: str
    skills: list[str]
    work_mode: WorkMode | None
    application_email: str | None


class OpportunityListResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    items: list[OpportunityAdminResponse]
    total: int
    page: int
    page_size: int
    pages: int


class OpportunityPublicListResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    items: list[OpportunityPublicResponse]
    total: int
    page: int
    page_size: int
    pages: int


def admin_settings_response(settings: CareersSettings) -> CareersSettingsAdminResponse:
    return CareersSettingsAdminResponse(
        id=settings.id,
        enabled=settings.enabled,
        heading=settings.heading,
        description=settings.description,
        application_email=settings.application_email,
        application_template=settings.application_template,
        created_at=settings.created_at,
        updated_at=settings.updated_at,
    )


def public_settings_response(settings: CareersSettings) -> CareersSettingsPublicResponse:
    if settings.enabled:
        return CareersSettingsPublicResponse(
            enabled=True,
            heading=settings.heading or None,
            description=settings.description or None,
            application_template=settings.application_template,
        )
    return CareersSettingsPublicResponse(
        enabled=False, heading=None, description=None, application_template=None
    )


def _admin_opportunity(opportunity: Opportunity) -> OpportunityAdminResponse:
    return OpportunityAdminResponse(
        id=opportunity.id,
        title=opportunity.title,
        slug=opportunity.slug,
        type=opportunity.type,
        custom_type=opportunity.custom_type,
        description=opportunity.description,
        skills=opportunity.skills,
        work_mode=opportunity.work_mode,
        application_email=opportunity.application_email,
        status=opportunity.status,
        display_order=opportunity.display_order,
        created_at=opportunity.created_at,
        updated_at=opportunity.updated_at,
    )


def _public_opportunity(
    opportunity: Opportunity, default_email: str | None
) -> OpportunityPublicResponse:
    return OpportunityPublicResponse(
        slug=opportunity.slug,
        title=opportunity.title,
        type=opportunity.type,
        custom_type=opportunity.custom_type,
        description=opportunity.description,
        skills=opportunity.skills,
        work_mode=opportunity.work_mode,
        application_email=opportunity.application_email or default_email,
    )


def admin_opportunity_response(opportunity: Opportunity) -> OpportunityAdminResponse:
    return _admin_opportunity(opportunity)


def public_opportunity_response(
    opportunities: list[Opportunity], default_email: str | None
) -> list[OpportunityPublicResponse]:
    return [_public_opportunity(item, default_email) for item in opportunities]