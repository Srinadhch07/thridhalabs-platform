"""Media library API (Phase 3): upload, list, retrieve, file serving, delete.

All endpoints require Phase 2 authentication; upload/delete additionally
require the double-submit CSRF header. Roles: upload = editor+, delete =
admin+. Serving (file bytes) is restricted to authenticated admins — arbitrary
keys are never accepted; variants are validated against the media document.
"""

from __future__ import annotations

import math
from typing import Literal

from fastapi import APIRouter, Depends, File, Query, Response, UploadFile

from app.core.config import get_settings
from app.core.errors import AppError
from app.deps.auth import get_active_admin, require_role
from app.deps.csrf import require_csrf
from app.models.admin import Admin
from app.modules.auth.schemas import StatusResponse
from app.modules.media import service
from app.modules.media.schemas import (
    MediaListResponse,
    MediaResponse,
    media_to_response,
)

router = APIRouter(prefix="/media", tags=["media"])

_ERROR_RESPONSES = {
    401: {"description": "Authentication required"},
    403: {"description": "CSRF failure, disabled account or insufficient role"},
    404: {"description": "Media, variant or stored file not found"},
    413: {"description": "Upload exceeds PRODUCT_IMAGE_MAX_BYTES"},
    415: {"description": "Unsupported media type (only JPEG, PNG, WebP)"},
    422: {"description": "Invalid/corrupt image or excessive dimensions"},
    500: {"description": "Storage or media-record failure"},
}


@router.post(
    "",
    status_code=201,
    response_model=MediaResponse,
    dependencies=[Depends(require_csrf)],
    responses=_ERROR_RESPONSES,
    summary="Upload a media asset",
)
async def upload(
    file: UploadFile = File(..., description="JPEG, PNG or WebP image"),
    response: Response = None,
    admin: Admin = Depends(require_role("editor")),
) -> MediaResponse:
    """Validate, process and store an image.

    The declared Content-Type/extension are ignored — the file's actual bytes
    must be a decodable JPEG, PNG or WebP image no larger than
    `PRODUCT_IMAGE_MAX_BYTES`. Returns 200 instead of 201 when identical
    content was already uploaded (de-duplication).
    """
    settings = get_settings()
    limit = settings.PRODUCT_IMAGE_MAX_BYTES
    data = bytearray()
    while True:
        chunk = await file.read(1024 * 1024)
        if not chunk:
            break
        data.extend(chunk)
        if len(data) > limit:
            raise AppError(
                413,
                "FILE_TOO_LARGE",
                f"File exceeds the {limit} byte upload limit",
            )

    result = await service.upload_media(
        data=bytes(data),
        original_name=file.filename,
        created_by=admin.id,
    )
    if not result.created:
        response.status_code = 200
    return media_to_response(result.media)


@router.get(
    "",
    response_model=MediaListResponse,
    responses=_ERROR_RESPONSES,
    summary="List media (paginated)",
)
async def list_media(
    page: int = Query(1, ge=1, description="Page number (1-based)"),
    page_size: int = Query(
        20, ge=1, le=100, description="Items per page (max 100)"
    ),
    sort: Literal["newest", "oldest"] = Query("newest"),
    admin: Admin = Depends(get_active_admin),
) -> MediaListResponse:
    items, total = await service.list_media(
        page=page, page_size=page_size, sort=sort
    )
    pages = math.ceil(total / page_size) if total else 0
    return MediaListResponse(
        items=[media_to_response(media) for media in items],
        total=total,
        page=page,
        page_size=page_size,
        pages=pages,
    )


@router.get(
    "/{media_id}",
    response_model=MediaResponse,
    responses=_ERROR_RESPONSES,
    summary="Get media metadata",
)
async def get_media(
    media_id: str, admin: Admin = Depends(get_active_admin)
) -> MediaResponse:
    media = await service.get_media(media_id)
    return media_to_response(media)


@router.get(
    "/{media_id}/file",
    responses=_ERROR_RESPONSES,
    summary="Get stored media bytes for a validated variant",
)
async def get_media_file(
    media_id: str,
    variant: str = Query("original", description="Variant name"),
    admin: Admin = Depends(get_active_admin),
) -> Response:
    data, mime_type = await service.get_media_file(media_id, variant)
    return Response(
        content=data,
        media_type=mime_type,
        headers={"Cache-Control": "private, max-age=3600"},
    )


@router.delete(
    "/{media_id}",
    response_model=StatusResponse,
    dependencies=[Depends(require_csrf)],
    responses=_ERROR_RESPONSES,
    summary="Delete media (deletes all stored variants)",
)
async def delete_media(
    media_id: str, admin: Admin = Depends(require_role("admin"))
) -> StatusResponse:
    await service.delete_media(media_id)
    return StatusResponse()