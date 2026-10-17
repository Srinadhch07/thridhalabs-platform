"""Media service — the only component that talks to storage providers.

Owns the upload pipeline (size limit -> content detection -> Pillow processing
-> store variants -> create document), duplicate detection, controlled
retrieval/list/delete, and cleanup of partially-stored objects on failure.
"""

from __future__ import annotations

import asyncio
import os
from dataclasses import dataclass
from datetime import datetime, timezone

from app.core.config import get_settings
from app.core.errors import AppError
from app.core.logging import get_logger
from app.models.media import Media, MediaType, MediaVariant
from app.modules.media import repository
from app.modules.media.processing import (
    VARIANT_NAMES,
    ImageTooLargeError,
    InvalidImageError,
    ProcessedImage,
    VariantOutput,
    detect_image_format,
    process_image,
    sha256_checksum,
)
from app.storage import get_storage_provider
from app.storage.base import StorageError, StorageObjectNotFoundError

log = get_logger("media")


@dataclass(frozen=True)
class UploadResult:
    media: Media
    created: bool


def _safe_original_name(filename: str | None) -> str:
    """Display-only name. Never used to build storage keys or filesystem paths."""
    name = (filename or "").replace("\\", "/").strip().rstrip("/")
    return os.path.basename(name)[:255] or "upload"


def _build_keys(checksum: str, now: datetime | None = None) -> dict[str, str]:
    now = now or datetime.now(timezone.utc)
    base = f"media/{now.year}/{now.month:02d}/{checksum}"
    return {name: f"{base}/{name}.webp" for name in VARIANT_NAMES}


def _variant_model(variant: VariantOutput, key: str) -> MediaVariant:
    return MediaVariant(
        name=variant.name,
        object_key=key,
        width=variant.width,
        height=variant.height,
        size_bytes=variant.size_bytes,
        mime_type=variant.mime_type,
    )


async def _cleanup_objects(provider, keys: list[str]) -> None:
    for key in keys:
        try:
            await provider.delete(key)
        except Exception:  # best-effort cleanup must not mask the real error
            log.warning("Cleanup failed to delete object %s", key)


async def upload_media(
    *, data: bytes, original_name: str | None, created_by: str
) -> UploadResult:
    """Validate, process, store and index an uploaded image.

    Returns `UploadResult(media, created=False)` when a media record with the
    same content hash already exists in the same storage mode (de-duplication —
    nothing new is stored and the existing record is returned).
    """
    settings = get_settings()

    if not data:
        raise AppError(422, "EMPTY_FILE", "The uploaded file is empty")

    max_bytes = settings.PRODUCT_IMAGE_MAX_BYTES
    if len(data) > max_bytes:
        raise AppError(
            413,
            "FILE_TOO_LARGE",
            f"File exceeds the {max_bytes} byte upload limit",
        )

    checksum = sha256_checksum(data)

    existing = await repository.find_by_checksum_and_mode(
        checksum, settings.STORAGE_MODE
    )
    if existing is not None:
        log.info(
            "De-duplicated upload (checksum %s…%s) — reusing media %s",
            checksum[:8],
            checksum[-4:],
            existing.id,
        )
        return UploadResult(media=existing, created=False)

    detected = detect_image_format(data)
    if detected is None:
        raise AppError(
            415,
            "UNSUPPORTED_MEDIA_TYPE",
            "Only JPEG, PNG and WebP images are supported",
        )

    try:
        processed: ProcessedImage = await asyncio.to_thread(
            process_image, data, settings
        )
    except ImageTooLargeError as exc:
        raise AppError(
            422, "IMAGE_TOO_LARGE", "Image dimensions exceed the safety limit"
        ) from exc
    except InvalidImageError as exc:
        raise AppError(
            422, "INVALID_IMAGE", "File is not a valid JPEG, PNG or WebP image"
        ) from exc

    provider = get_storage_provider()
    keys = _build_keys(checksum)

    stored_keys: list[str] = []
    try:
        for variant in processed.variants:
            key = keys[variant.name]
            await provider.put(key, variant.data, content_type="image/webp")
            stored_keys.append(key)
    except StorageError as exc:
        await _cleanup_objects(provider, stored_keys)
        log.error(
            "Upload failed during storage write — %s object(s) cleaned up (%s)",
            len(stored_keys),
            type(exc).__name__,
        )
        raise AppError(500, "STORAGE_ERROR", "Could not store the uploaded media") from exc

    variant_models = [
        _variant_model(variant, keys[variant.name])
        for variant in processed.variants
    ]

    try:
        media = await repository.insert_media(
            original_name=_safe_original_name(original_name),
            format=processed.format,
            mime_type=processed.mime_type,
            media_type=MediaType.IMAGE.value,
            size_bytes=len(data),
            width=processed.width,
            height=processed.height,
            checksum=checksum,
            storage_mode=provider.mode,
            object_key=keys["original"],
            variants=variant_models,
            created_by=created_by,
        )
    except Exception as exc:
        await _cleanup_objects(provider, stored_keys)
        log.error(
            "Upload DB insert failed — %s object(s) cleaned up (%s)",
            len(stored_keys),
            type(exc).__name__,
        )
        raise AppError(
            500, "MEDIA_CREATE_FAILED", "The media record could not be created"
        ) from exc

    log.info(
        "Media uploaded id=%s size=%d mode=%s format=%s checksum=%s…%s created_by=%s",
        media.id,
        media.size_bytes,
        media.storage_mode,
        processed.format,
        checksum[:8],
        checksum[-4:],
        created_by,
    )
    return UploadResult(media=media, created=True)


async def get_media(media_id: str) -> Media:
    media = await repository.find_by_id(media_id)
    if media is None:
        raise AppError(404, "MEDIA_NOT_FOUND", "Media was not found")
    return media


async def list_media(
    *, page: int = 1, page_size: int = 20, sort: str = "newest"
) -> tuple[list[Media], int]:
    return await repository.list_media(
        page=page, page_size=page_size, newest=(sort == "newest")
    )


async def list_member_media(
    *, creator_id: str, page: int = 1, page_size: int = 20, sort: str = "newest"
) -> tuple[list[Media], int]:
    """List media owned by a single member (their own uploads only)."""
    return await repository.list_by_creator(
        created_by=creator_id,
        page=page,
        page_size=page_size,
        newest=(sort == "newest"),
    )


async def get_media_file(
    media_id: str, variant_name: str
) -> tuple[bytes, str]:
    """Return (stored bytes, mime type) for a validated variant of a media doc.

    The variant name is checked against the document — arbitrary object keys
    are never accepted from callers.
    """
    media = await get_media(media_id)
    variant = next(
        (v for v in media.variants if v.name == variant_name), None
    )
    if variant is None:
        raise AppError(404, "INVALID_VARIANT", "Unknown media variant")

    provider = get_storage_provider()
    try:
        data = await provider.get(variant.object_key)
    except StorageObjectNotFoundError as exc:
        raise AppError(
            404, "MEDIA_FILE_NOT_FOUND", "The stored file could not be found"
        ) from exc
    except StorageError as exc:
        log.error("Failed to read media %s variant %s (%s)", media_id, variant_name, type(exc).__name__)
        raise AppError(
            500, "STORAGE_ERROR", "Could not read the stored media"
        ) from exc

    return data, variant.mime_type


async def delete_media(media_id: str) -> None:
    """Delete every stored variant, then the media document.

    Storage deletion runs first and every stored object must be deleted before
    the document is removed — otherwise the API reports failure and the record
    survives so a retry can converge (provider deletions are idempotent).
    """
    media = await get_media(media_id)
    provider = get_storage_provider()

    failures = 0
    for variant in media.variants:
        try:
            await provider.delete(variant.object_key)
        except StorageError:
            failures += 1
            log.error("Failed to delete object %s", variant.object_key)

    if failures:
        log.error(
            "Media delete incomplete for %s — %d/%d object(s) failed",
            media_id,
            failures,
            len(media.variants),
        )
        raise AppError(
            500,
            "STORAGE_DELETE_FAILED",
            "Some stored objects could not be deleted; the record was kept",
        )

    await repository.delete_by_id(media_id)
    log.info("Media deleted id=%s (4 variants)", media_id)