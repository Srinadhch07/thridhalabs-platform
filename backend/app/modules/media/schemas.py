"""Pydantic schemas for the media API.

API boundaries expose clean models only: never raw MongoDB documents, never
filesystem paths, never AWS/credentials, never internal provider objects.
"""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.core.config import get_settings
from app.models.media import Media, MediaType


class MediaVariantResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str
    object_key: str
    width: int
    height: int
    size_bytes: int
    mime_type: str


class MediaResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    original_name: str
    format: str
    mime_type: str
    media_type: MediaType
    size_bytes: int
    width: int
    height: int
    checksum: str
    storage_mode: str
    variants: list[MediaVariantResponse]
    urls: dict[str, str]
    created_by: str
    created_at: datetime
    updated_at: datetime


def media_to_response(media: Media) -> MediaResponse:
    """Map a media document to its API model.

    `urls` point at the controlled, authenticated file route — the same route
    serves both local and S3 objects, so S3 need never be public and no
    credentials are exposed.
    """
    prefix = get_settings().API_PREFIX.rstrip("/")
    urls: dict[str, str] = {
        variant.name: f"{prefix}/media/{media.id}/file?variant={variant.name}"
        for variant in media.variants
    }
    return MediaResponse(
        id=media.id,
        original_name=media.original_name,
        format=media.format,
        mime_type=media.mime_type,
        media_type=media.media_type,
        size_bytes=media.size_bytes,
        width=media.width,
        height=media.height,
        checksum=media.checksum,
        storage_mode=media.storage_mode,
        variants=[MediaVariantResponse(**variant.model_dump()) for variant in media.variants],
        urls=urls,
        created_by=media.created_by,
        created_at=media.created_at,
        updated_at=media.updated_at,
    )


class MediaListResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    items: list[MediaResponse]
    total: int
    page: int
    page_size: int
    pages: int