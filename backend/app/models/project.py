"""Project domain model with explicit publishing/type enums.

Publishing rules are enforced server-side: only `published` projects are ever
visible through public APIs; drafts are never exposed; archived projects are
excluded from public listings unless a future phase explicitly chooses to.
"""

from __future__ import annotations

from datetime import date, datetime
from enum import Enum

from pydantic import BaseModel, ConfigDict


class ProjectStatus(str, Enum):
    DRAFT = "draft"
    PUBLISHED = "published"
    ARCHIVED = "archived"


class ProjectType(str, Enum):
    CLIENT_WORK = "client-work"
    PRODUCT = "product"
    EXPERIMENT = "experiment"
    MEMBER_CONTRIBUTION = "member-contribution"


class Project(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    name: str
    slug: str
    thumbnail_media_id: str | None = None
    gallery_media_ids: list[str] = []
    description: str = ""
    client_id: str | None = None
    category: str | None = None
    technologies: list[str] = []
    live_url: str | None = None
    github_url: str | None = None
    status: ProjectStatus = ProjectStatus.DRAFT
    project_type: ProjectType
    featured: bool = False
    display_order: int = 0
    completion_date: date | None = None
    created_at: datetime
    updated_at: datetime