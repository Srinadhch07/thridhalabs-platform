"""Legal documents schemas."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class LegalAdminResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    slug: Literal["privacy-policy", "terms-and-conditions", "cookie-policy"]
    title: str
    content_markdown: str
    status: Literal["draft", "published"]
    created_at: datetime
    updated_at: datetime
    published_at: datetime | None = None


class LegalListResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    items: list[LegalAdminResponse]


class LegalPublicResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    slug: Literal["privacy-policy", "terms-and-conditions", "cookie-policy"]
    title: str
    content_markdown: str
    updated_at: datetime | None = None
    published_at: datetime | None = None


class LegalSaveDraftRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str | None = Field(default=None, max_length=200)
    content_markdown: str = Field(default="", max_length=200000)
    expected_updated_at: datetime | None = None


class LegalPublishRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str | None = Field(default=None, max_length=200)
    content_markdown: str | None = Field(default=None, max_length=200000)
    expected_updated_at: datetime | None = None
