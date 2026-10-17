"""Pydantic schemas for the testimonials API (admin + public).

Moderation model: `status` (pending/approved/rejected) is owned exclusively
by the server/admins; `published` gates public visibility and `featured`
boosts an item to homepage-level surfaces. Public APIs only ever expose
approved + published items — bots and direct URL access can never see
anything else.
"""

from __future__ import annotations

from datetime import datetime
from datetime import date as DateValue

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.core.validators import non_empty_name
from app.models.testimonial import TestimonialStatus

MAX_TEXT_LENGTH = 5000


class TestimonialCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    client_id: str | None = None
    person_name: str
    role: str = Field(default="", max_length=200)
    testimonial_text: str = Field(max_length=MAX_TEXT_LENGTH)
    profile_image_media_id: str | None = None
    company: str | None = Field(default=None, max_length=200)
    rating: int = Field(default=5, ge=1, le=5)
    featured: bool = False
    published: bool = False
    status: TestimonialStatus | None = None
    display_order: int = Field(default=0, ge=0)
    date: DateValue | None = None

    @field_validator("person_name")
    @classmethod
    def _person(cls, value: str) -> str:
        return non_empty_name(value, max_length=200)

    @field_validator("role")
    @classmethod
    def _role(cls, value: str) -> str:
        value = value.strip()
        if len(value) > 200:
            raise ValueError("Must be at most 200 characters")
        return value

    @field_validator("testimonial_text")
    @classmethod
    def _text(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Must not be empty")
        return value

    @field_validator("company")
    @classmethod
    def _company(cls, value: str | None) -> str | None:
        if value is None:
            return None
        value = value.strip()
        return value or None


class TestimonialUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    client_id: str | None = None
    person_name: str | None = None
    role: str | None = Field(default=None, max_length=200)
    testimonial_text: str | None = Field(default=None, max_length=MAX_TEXT_LENGTH)
    profile_image_media_id: str | None = None
    company: str | None = Field(default=None, max_length=200)
    rating: int | None = Field(default=None, ge=1, le=5)
    featured: bool | None = None
    published: bool | None = None
    status: TestimonialStatus | None = None
    display_order: int | None = Field(default=None, ge=0)
    date: DateValue | None = None

    @field_validator("person_name")
    @classmethod
    def _person(cls, value: str | None) -> str | None:
        return non_empty_name(value, max_length=200) if value is not None else None

    @field_validator("role")
    @classmethod
    def _role(cls, value: str | None) -> str | None:
        if value is None:
            return None
        value = value.strip()
        if len(value) > 200:
            raise ValueError("Must be at most 200 characters")
        return value

    @field_validator("testimonial_text")
    @classmethod
    def _text(cls, value: str | None) -> str | None:
        if value is None:
            return None
        value = value.strip()
        if not value:
            raise ValueError("Must not be empty")
        return value

    @field_validator("company")
    @classmethod
    def _company(cls, value: str | None) -> str | None:
        if value is None:
            return None
        value = value.strip()
        return value or None


class TestimonialSubmit(BaseModel):
    """Public submission payload. `extra="ignore"` is deliberate: any
    client-provided moderation fields (`status`, `published`, `featured`,
    `client_id`, …) are silently dropped and the server forces
    pending/unpublished/unfeatured."""

    model_config = ConfigDict(extra="ignore")

    person_name: str
    role: str = Field(default="", max_length=200)
    company: str | None = Field(default=None, max_length=200)
    testimonial_text: str = Field(max_length=MAX_TEXT_LENGTH)
    rating: int = Field(default=5, ge=1, le=5)

    @field_validator("person_name")
    @classmethod
    def _person(cls, value: str) -> str:
        return non_empty_name(value, max_length=200)

    @field_validator("role")
    @classmethod
    def _role(cls, value: str) -> str:
        value = value.strip()
        if len(value) > 200:
            raise ValueError("Must be at most 200 characters")
        return value

    @field_validator("testimonial_text")
    @classmethod
    def _text(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Must not be empty")
        return value

    @field_validator("company")
    @classmethod
    def _company(cls, value: str | None) -> str | None:
        if value is None:
            return None
        value = value.strip()
        return value or None


class TestimonialSubmissionResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    message: str


# --------------------------------------------------------------------------
# Responses
# --------------------------------------------------------------------------
class ClientRef(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    slug: str
    name: str


class ClientPublicRef(BaseModel):
    model_config = ConfigDict(extra="forbid")

    slug: str
    name: str


class TestimonialAdminResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    client_id: str | None
    client: ClientRef | None
    person_name: str
    role: str
    testimonial_text: str
    profile_image_media_id: str | None
    company: str | None
    rating: int
    featured: bool
    published: bool
    status: TestimonialStatus
    display_order: int
    date: DateValue | None
    created_at: datetime
    updated_at: datetime


class TestimonialPublicResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    person_name: str
    role: str
    testimonial_text: str
    profile_image_media_id: str | None
    company: str | None
    rating: int
    featured: bool
    display_order: int
    date: DateValue | None
    client: ClientPublicRef | None


class TestimonialListResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    items: list[TestimonialAdminResponse]
    total: int
    page: int
    page_size: int
    pages: int


class TestimonialPublicListResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    items: list[TestimonialPublicResponse]
    total: int
    page: int
    page_size: int
    pages: int
