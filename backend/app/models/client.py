"""Client domain model. Projects/testimonials reference clients by id only —
no project documents are embedded here."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict


class Client(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    name: str
    slug: str
    logo_media_id: str | None = None
    featured_image_media_id: str | None = None
    description: str = ""
    website: str | None = None
    industry: str | None = None
    category: str | None = None
    featured: bool = False
    display_order: int = 0
    created_at: datetime
    updated_at: datetime