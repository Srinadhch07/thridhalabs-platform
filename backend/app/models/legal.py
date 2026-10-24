"""Legal documents domain model.

Three supported documents: privacy-policy, terms-and-conditions, cookie-policy.
Each has draft/published state; public endpoints only return published content.
"""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

LegalSlug = Literal["privacy-policy", "terms-and-conditions", "cookie-policy"]
LegalStatus = Literal["draft", "published"]


class LegalDocument(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    slug: LegalSlug
    title: str
    content_markdown: str = ""
    status: LegalStatus = "draft"
    created_at: datetime
    updated_at: datetime
    published_at: datetime | None = None


class LegalDocumentPublic(BaseModel):
    model_config = ConfigDict(extra="forbid")

    slug: LegalSlug
    title: str
    content_markdown: str
    updated_at: datetime | None = None
    published_at: datetime | None = None
