"""Pydantic schemas for the clients API (admin + public)."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.core.validators import non_empty_name, optional_http_url

MAX_TEXT_LENGTH = 5000


def _optional_piece(value: str | None, max_length: int) -> str | None:
    if value is None:
        return None
    value = value.strip()
    if len(value) > max_length:
        raise ValueError(f"Must be at most {max_length} characters")
    return value or None


class ClientCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str
    slug: str | None = None
    logo_media_id: str | None = None
    featured_image_media_id: str | None = None
    description: str = Field(default="", max_length=MAX_TEXT_LENGTH)
    website: str | None = None
    industry: str | None = Field(default=None, max_length=100)
    category: str | None = Field(default=None, max_length=100)
    featured: bool = False
    display_order: int = Field(default=0, ge=0)

    @field_validator("name")
    @classmethod
    def _name(cls, value: str) -> str:
        return non_empty_name(value)

    @field_validator("website")
    @classmethod
    def _website(cls, value: str | None) -> str | None:
        return optional_http_url(value)

    @field_validator("industry", "category")
    @classmethod
    def _pieces(cls, value: str | None) -> str | None:
        return _optional_piece(value, 100)


class ClientUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str | None = None
    slug: str | None = None
    logo_media_id: str | None = None
    featured_image_media_id: str | None = None
    description: str | None = Field(default=None, max_length=MAX_TEXT_LENGTH)
    website: str | None = None
    industry: str | None = Field(default=None, max_length=100)
    category: str | None = Field(default=None, max_length=100)
    featured: bool | None = None
    display_order: int | None = Field(default=None, ge=0)

    @field_validator("name")
    @classmethod
    def _name(cls, value: str | None) -> str | None:
        return non_empty_name(value) if value is not None else None

    @field_validator("website")
    @classmethod
    def _website(cls, value: str | None) -> str | None:
        return optional_http_url(value)

    @field_validator("industry", "category")
    @classmethod
    def _pieces(cls, value: str | None) -> str | None:
        return _optional_piece(value, 100)


# --------------------------------------------------------------------------
# Responses
# --------------------------------------------------------------------------
class ClientAdminResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    name: str
    slug: str
    logo_media_id: str | None
    featured_image_media_id: str | None
    description: str
    website: str | None
    industry: str | None
    category: str | None
    featured: bool
    display_order: int
    project_ids: list[str]
    created_at: datetime
    updated_at: datetime


class ClientProjectRef(BaseModel):
    """Public reference to a published project (used instead of raw IDs)."""

    model_config = ConfigDict(extra="forbid")

    slug: str
    name: str


class ClientPublicResponse(BaseModel):
    """Safe public client. Internal Mongo ids are not exposed; projects are
    referenced by slug only and never include drafts/archived work."""

    model_config = ConfigDict(extra="forbid")

    slug: str
    name: str
    logo_media_id: str | None
    featured_image_media_id: str | None
    description: str
    website: str | None
    industry: str | None
    category: str | None
    featured: bool
    display_order: int
    projects: list[ClientProjectRef]


class ClientListResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    items: list[ClientAdminResponse]
    total: int
    page: int
    page_size: int
    pages: int


class ClientPublicListResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    items: list[ClientPublicResponse]
    total: int
    page: int
    page_size: int
    pages: int