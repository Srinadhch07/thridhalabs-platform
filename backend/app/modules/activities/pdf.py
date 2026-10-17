"""PDF brief validation + storage for activities.

The media pipeline is deliberately images-only, so PDF briefs get their own
small, equally strict path: the uploaded bytes must actually begin with a PDF
header (filename and Content-Type are ignored), the size limit is enforced
before storage, and objects are stored through the shared `StorageProvider`
under a content-derived, activity-scoped key. Callers never supply object keys.
"""

from __future__ import annotations

import hashlib
import os

from app.core.errors import AppError
from app.core.logging import get_logger
from app.storage import get_storage_provider
from app.storage.base import StorageError, StorageObjectNotFoundError

log = get_logger("activities.pdf")

PDF_MIME = "application/pdf"
_KEY_PREFIX = "activity-briefs"
# A conformant PDF starts with "%PDF-"; the spec tolerates a small amount of
# leading junk before the header, so we search a bounded prefix instead of
# requiring byte 0 to match.
_PDF_MAGIC = b"%PDF-"
_MAGIC_SCAN_BYTES = 1024
_MAX_FILENAME_LENGTH = 255


def safe_filename(filename: str | None) -> str:
    """Display-only filename. Never used to build storage keys or paths."""
    name = (filename or "").replace("\\", "/").strip().rstrip("/")
    base = os.path.basename(name)[:_MAX_FILENAME_LENGTH]
    return base or "brief.pdf"


def pdf_checksum(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def validate_pdf_bytes(data: bytes, *, max_bytes: int) -> None:
    """Reject empty, oversized or non-PDF payloads with a controlled error."""
    if not data:
        raise AppError(422, "EMPTY_FILE", "The uploaded file is empty")
    if len(data) > max_bytes:
        raise AppError(
            413,
            "FILE_TOO_LARGE",
            f"File exceeds the {max_bytes} byte upload limit",
        )
    if _PDF_MAGIC not in data[:_MAGIC_SCAN_BYTES]:
        raise AppError(
            415,
            "UNSUPPORTED_MEDIA_TYPE",
            "Only PDF files are supported for activity briefs",
        )


def brief_object_key(activity_id: str, version: int) -> str:
    return f"{_KEY_PREFIX}/{activity_id}/v{version:04d}.pdf"


async def store_brief(object_key: str, data: bytes) -> None:
    """Store brief bytes. Raises AppError 500 on provider failure."""
    provider = get_storage_provider()
    try:
        await provider.put(object_key, data, content_type=PDF_MIME)
    except StorageError as exc:
        log.error("Brief storage write failed (%s)", type(exc).__name__)
        raise AppError(500, "STORAGE_ERROR", "Could not store the brief") from exc


async def read_brief(object_key: str) -> bytes:
    """Read brief bytes for a *known* key. Raises AppError 404/500."""
    provider = get_storage_provider()
    try:
        return await provider.get(object_key)
    except StorageObjectNotFoundError as exc:
        raise AppError(
            404, "BRIEF_FILE_NOT_FOUND", "The stored brief could not be found"
        ) from exc
    except StorageError as exc:
        log.error("Brief storage read failed (%s)", type(exc).__name__)
        raise AppError(500, "STORAGE_ERROR", "Could not read the stored brief") from exc


async def delete_brief_object(object_key: str) -> None:
    """Best-effort delete of a brief object (idempotent)."""
    provider = get_storage_provider()
    try:
        await provider.delete(object_key)
    except StorageError:
        log.warning("Failed to delete brief object %s", object_key)
