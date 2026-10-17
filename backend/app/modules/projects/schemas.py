"""Pydantic schemas for the projects API (admin + public).

Public responses never expose drafts or archived projects (enforced in the
service) and never leak internal client ids — clients are referenced by slug.
"""

from __future__ import annotations

from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.core.validators import non_empty_name, optional_http_url
from app.models.project import ProjectStatus, ProjectType

MAX_TEXT_LENGTH = 5000
MAX_TECHNOLOGIES = 50


def _list_of_strings(value: list[str], max_items: int, item_max: int) -> list[str]:
    cleaned = [item.strip()[:item_max] for item in value if item.strip()]
    return list(dict.fromkeys(cleaned))[:max_items]


class ProjectCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str
    slug: str | None = None
    thumbnail_media_id: str | None = None
    gallery_media_ids: list[str] = Field(default_factory=list)
    description: str = Field(default="", max_length=MAX_TEXT_LENGTH)
    client_id: str | None = None
    category: str | None = Field(default=None, max_length=100)
    technologies: list[str] = Field(default_factory=list)
    live_url: str | None = None
    github_url: str | None = None
    status: ProjectStatus = ProjectStatus.DRAFT
    project_type: ProjectType
    featured: bool = False
    display_order: int = Field(default=0, ge=0)
    completion_date: date | None = None

    @field_validator("name")
    @classmethod
    def _name(cls, value: str) -> str:
        return non_empty_name(value)

    @field_validator("live_url", "github_url")
    @classmethod
    def _urls(cls, value: str | None) -> str | None:
        return optional_http_url(value)

    @field_validator("technologies")
    @classmethod
    def _techs(cls, value: list[str]) -> list[str]:
        return _list_of_strings(value, MAX_TECHNOLOGIES, 60)


class ProjectUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str | None = None
    slug: str | None = None
    thumbnail_media_id: str | None = None
    gallery_media_ids: list[str] | None = Field(default=None)
    description: str | None = Field(default=None, max_length=MAX_TEXT_LENGTH)
    client_id: str | None = None
    category: str | None = Field(default=None, max_length=100)
    technologies: list[str] | None = None
    live_url: str | None = None
    github_url: str | None = None
    status: ProjectStatus | None = None
    project_type: ProjectType | None = None
    featured: bool | None = None
    display_order: int | None = Field(default=None, ge=0)
    completion_date: date | None = None

    @field_validator("name")
    @classmethod
    def _name(cls, value: str | None) -> str | None:
        return non_empty_name(value) if value is not None else None

    @field_validator("live_url", "github_url")
    @classmethod
    def _urls(cls, value: str | None) -> str | None:
        return optional_http_url(value)

    @field_validator("technologies")
    @classmethod
    def _techs(cls, value: list[str] | None) -> list[str] | None:
        if value is None:
            return None
        return _list_of_strings(value, MAX_TECHNOLOGIES, 60)


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


class ProjectAdminResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    name: str
    slug: str
    thumbnail_media_id: str | None
    gallery_media_ids: list[str]
    description: str
    client_id: str | None
    client: ClientRef | None
    category: str | None
    technologies: list[str]
    live_url: str | None
    github_url: str | None
    status: ProjectStatus
    project_type: ProjectType
    featured: bool
    display_order: int
    completion_date: date | None
    created_at: datetime
    updated_at: datetime


class ProjectPublicResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    slug: str
    name: str
    thumbnail_media_id: str | None
    gallery_media_ids: list[str]
    description: str
    client: ClientPublicRef | None
    category: str | None
    technologies: list[str]
    live_url: str | None
    github_url: str | None
    project_type: ProjectType
    featured: bool
    display_order: int
    completion_date: date | None


class ProjectListResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    items: list[ProjectAdminResponse]
    total: int
    page: int
    page_size: int
    pages: int


class ProjectPublicListResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    items: list[ProjectPublicResponse]
    total: int
    page: int
    page_size: int
    pages: int