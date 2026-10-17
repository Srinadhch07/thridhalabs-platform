"""Public media delivery — unauthenticated, read-only image serving.

Unlike the admin media route (`/api/media/{id}/file`, auth required), this
endpoint is designed for public, same-origin hot-linking by the website. It is
read-only and resolves media strictly through the database — the client never
supplies an object key, bucket, filesystem path or traversal segment.

Caching: variant payloads are derived from the media id + variant name and are
content-addressed (immutable), so aggressive, public cache headers are safe.
"""

from __future__ import annotations

from typing import Literal

from fastapi import APIRouter, Depends, Query, Response

from app.deps.maintenance import require_public_site_available
from app.modules.media import service

router = APIRouter(
    prefix="/public/media",
    tags=["public"],
    dependencies=[Depends(require_public_site_available)],
)

_CACHE = "public, max-age=31536000, immutable"

_VARIANT = Literal["original", "thumb", "md", "lg"]


@router.get(
    "/{media_id}",
    summary="Serve a stored media variant publicly",
    responses={
        404: {"description": "Unknown media id"},
        422: {"description": "Unknown variant name"},
    },
)
async def get_public_media(
    media_id: str,
    variant: _VARIANT = Query("md", description="Variant name"),
) -> Response:
    """Return the bytes of a validated variant for a known media document.

    Unknown/invalid ids return 404; arbitrary keys are never accepted (the
    variant name is cross-checked against the media document).
    """
    data, mime_type = await service.get_media_file(media_id, variant)
    return Response(
        content=data,
        media_type=mime_type,
        headers={"Cache-Control": _CACHE},
    )