"""Shared cross-entity reference validation.

Media references across settings/branding/clients/projects/testimonials must
point at existing media records; client references must point at existing
clients. Broken references are always rejected — never accepted silently.
"""

from __future__ import annotations

from app.core.errors import AppError
from app.modules.clients import repository as clients_repository
from app.modules.media import repository as media_repository


async def require_media_exist(media_ids: list[str]) -> None:
    """Raise AppError 400 when any referenced media record does not exist."""
    provided = {media_id for media_id in media_ids if media_id}
    if not provided:
        return
    found = await media_repository.find_many_by_id(list(provided))
    missing = provided - set(found)
    if missing:
        raise AppError(
            400,
            "INVALID_MEDIA_REFERENCE",
            "One or more referenced media records do not exist",
        )


async def require_client_exists(client_id: str | None) -> None:
    """Raise AppError 400 when the referenced client does not exist."""
    if not client_id:
        return
    client = await clients_repository.find_by_id(client_id)
    if client is None:
        raise AppError(
            400,
            "INVALID_CLIENT_REFERENCE",
            "The referenced client does not exist",
        )