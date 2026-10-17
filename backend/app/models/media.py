"""Media domain model and media types.

Media documents identify stored objects independently from any user-supplied
filename: the object key structure (`media/{year}/{month}/{checksum}/{variant}`)
is derived from content, never from upload input.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, ConfigDict


class MediaType(str, Enum):
    IMAGE = "image"


class MediaVariant(BaseModel):
    """A single stored variant of a media asset."""

    model_config = ConfigDict(extra="forbid")

    name: str  # "original" | "thumb" | "md" | "lg"
    object_key: str
    width: int
    height: int
    size_bytes: int
    mime_type: str


class Media(BaseModel):
    """Internal media representation. Never serialised to API responses
    directly — response schemas live in the media module."""

    model_config = ConfigDict(extra="forbid")

    id: str
    original_name: str  # display-only; never used to build storage keys
    format: str  # detected source format: "jpeg" | "png" | "webp"
    mime_type: str  # detected source MIME (content-based, not browser-supplied)
    media_type: MediaType
    size_bytes: int  # uploaded source size in bytes
    width: int  # normalized/pre-processed source dimensions
    height: int
    checksum: str  # SHA-256 of the uploaded source bytes (dedup)
    storage_mode: str  # "local" | "s3"
    object_key: str  # object key of the stored "original" variant
    variants: list[MediaVariant]
    created_by: str  # admin id
    created_at: datetime
    updated_at: datetime