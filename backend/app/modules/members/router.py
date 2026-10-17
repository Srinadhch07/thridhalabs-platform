"""Member portal API (`/member`): onboarding setup, login/logout, session,
profile, password change and profile picture.

Every mutation requires the double-submit CSRF header. Member sessions are
fully separate from admin sessions (see `app.deps.member_auth`).
"""

from __future__ import annotations

import math
from typing import Literal

from fastapi import APIRouter, Depends, File, Query, Request, Response, UploadFile

from app.core.config import get_settings
from app.core.errors import AppError
from app.deps.csrf import require_member_csrf
from app.deps.member_auth import get_current_member, get_enabled_member
from app.models.member import Member
from app.modules.auth.schemas import CsrfResponse, StatusResponse
from app.modules.members import service
from app.modules.members.schemas import (
    MemberLoginRequest,
    MemberMeResponse,
    MemberPasswordChangeRequest,
    MemberProfileResponse,
    MemberProfileUpdate,
    MemberSetupRequest,
)
from app.modules.media.schemas import (
    MediaListResponse,
    MediaResponse,
    media_to_response,
)

router = APIRouter(prefix="/member", tags=["member"])

_ERROR_RESPONSES = {
    400: {"description": "Invalid or expired setup link, or invalid change"},
    401: {"description": "Invalid credentials or invalid/revoked session"},
    403: {"description": "CSRF failure or disabled account"},
    404: {"description": "Member not found"},
    429: {"description": "Too many attempts"},
}


# --------------------------------------------------------------------------
# Onboarding + session
# --------------------------------------------------------------------------
@router.get(
    "/csrf",
    response_model=CsrfResponse,
    summary="Issue a member-scoped CSRF token (dedicated cookie)",
)
async def get_member_csrf(response: Response) -> CsrfResponse:
    """Bootstrap endpoint for the member double-submit CSRF pair. Sets the
    member CSRF cookie (never the Admin one) and returns the matching token."""
    token = service.issue_member_csrf(response)
    return CsrfResponse(csrfToken=token)


@router.post(
    "/setup",
    response_model=StatusResponse,
    dependencies=[Depends(require_member_csrf)],
    responses=_ERROR_RESPONSES,
    summary="Complete onboarding: set the account password",
)
async def setup(payload: MemberSetupRequest, request: Request) -> StatusResponse:
    await service.perform_setup(request, payload)
    return StatusResponse()


@router.post(
    "/login",
    response_model=StatusResponse,
    dependencies=[Depends(require_member_csrf)],
    responses=_ERROR_RESPONSES,
    summary="Member login",
)
async def login(
    payload: MemberLoginRequest, request: Request, response: Response
) -> StatusResponse:
    await service.perform_login(request, response, payload)
    return StatusResponse()


@router.post(
    "/logout",
    response_model=StatusResponse,
    dependencies=[Depends(require_member_csrf)],
    responses=_ERROR_RESPONSES,
    summary="Member logout (revokes the session)",
)
async def logout(
    response: Response, member: Member = Depends(get_enabled_member)
) -> StatusResponse:
    await service.perform_logout(response, member)
    return StatusResponse()


@router.get(
    "/me",
    response_model=MemberMeResponse,
    responses=_ERROR_RESPONSES,
    summary="Current authenticated member",
)
async def me(member: Member = Depends(get_current_member)) -> MemberMeResponse:
    return MemberMeResponse(
        id=member.id,
        member_id=member.member_id,
        email=member.email,
        status=member.status,
        full_name=member.full_name,
        profile_complete=member.profile_complete,
        last_login_at=member.last_login_at,
    )


# --------------------------------------------------------------------------
# Profile
# --------------------------------------------------------------------------
@router.get(
    "/profile",
    response_model=MemberProfileResponse,
    responses=_ERROR_RESPONSES,
    summary="Get the member's own profile",
)
async def get_profile(
    member: Member = Depends(get_enabled_member),
) -> MemberProfileResponse:
    return MemberProfileResponse.from_member(member)


@router.patch(
    "/profile",
    response_model=MemberProfileResponse,
    dependencies=[Depends(require_member_csrf)],
    responses=_ERROR_RESPONSES,
    summary="Update the member's own profile",
)
async def update_profile(
    payload: MemberProfileUpdate,
    member: Member = Depends(get_enabled_member),
) -> MemberProfileResponse:
    updated = await service.update_profile(member, payload)
    return MemberProfileResponse.from_member(updated)


@router.post(
    "/password",
    response_model=StatusResponse,
    dependencies=[Depends(require_member_csrf)],
    responses=_ERROR_RESPONSES,
    summary="Change the member's password",
)
async def change_password(
    payload: MemberPasswordChangeRequest,
    member: Member = Depends(get_enabled_member),
) -> StatusResponse:
    await service.change_password(member, payload)
    return StatusResponse()


# --------------------------------------------------------------------------
# Profile picture (shared media pipeline; member-owned assets only)
# --------------------------------------------------------------------------
@router.post(
    "/picture",
    response_model=MediaResponse,
    dependencies=[Depends(require_member_csrf)],
    responses={
        **_ERROR_RESPONSES,
        413: {"description": "Upload exceeds PRODUCT_IMAGE_MAX_BYTES"},
        415: {"description": "Unsupported media type (only JPEG, PNG, WebP)"},
        422: {"description": "Invalid/corrupt image or excessive dimensions"},
    },
    summary="Upload a profile picture",
)
async def upload_picture(
    file: UploadFile = File(..., description="JPEG, PNG or WebP image"),
    member: Member = Depends(get_enabled_member),
) -> MediaResponse:
    limit = get_settings().PRODUCT_IMAGE_MAX_BYTES
    data = bytearray()
    while True:
        chunk = await file.read(1024 * 1024)
        if not chunk:
            break
        data.extend(chunk)
        if len(data) > limit:
            raise AppError(
                413, "FILE_TOO_LARGE", f"File exceeds the {limit} byte upload limit"
            )
    media = await service.upload_profile_picture(
        member, data=bytes(data), original_name=file.filename
    )
    return media_to_response(media)


@router.delete(
    "/picture",
    response_model=MemberProfileResponse,
    dependencies=[Depends(require_member_csrf)],
    responses=_ERROR_RESPONSES,
    summary="Remove the member's profile picture",
)
async def delete_picture(
    member: Member = Depends(get_enabled_member),
) -> MemberProfileResponse:
    updated = await service.clear_profile_picture(member)
    return MemberProfileResponse.from_member(updated)


# --------------------------------------------------------------------------
# Media library (member-owned assets for the work showcase)
# --------------------------------------------------------------------------
@router.get(
    "/media",
    response_model=MediaListResponse,
    responses=_ERROR_RESPONSES,
    summary="List the member's own media (paginated)",
)
async def list_media(
    page: int = Query(1, ge=1, description="Page number (1-based)"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page (max 100)"),
    sort: Literal["newest", "oldest"] = Query("newest"),
    member: Member = Depends(get_enabled_member),
) -> MediaListResponse:
    items, total = await service.list_member_media(
        member, page=page, page_size=page_size, sort=sort
    )
    pages = math.ceil(total / page_size) if total else 0
    return MediaListResponse(
        items=[media_to_response(media) for media in items],
        total=total,
        page=page,
        page_size=page_size,
        pages=pages,
    )


@router.post(
    "/media",
    status_code=201,
    response_model=MediaResponse,
    dependencies=[Depends(require_member_csrf)],
    responses={
        **_ERROR_RESPONSES,
        409: {"description": "Identical content already owned by another account"},
        413: {"description": "Upload exceeds PRODUCT_IMAGE_MAX_BYTES"},
        415: {"description": "Unsupported media type (only JPEG, PNG, WebP)"},
        422: {"description": "Invalid/corrupt image or excessive dimensions"},
    },
    summary="Upload an image to the member's own media library",
)
async def upload_media(
    file: UploadFile = File(..., description="JPEG, PNG or WebP image"),
    response: Response = None,
    member: Member = Depends(get_enabled_member),
) -> MediaResponse:
    limit = get_settings().PRODUCT_IMAGE_MAX_BYTES
    data = bytearray()
    while True:
        chunk = await file.read(1024 * 1024)
        if not chunk:
            break
        data.extend(chunk)
        if len(data) > limit:
            raise AppError(
                413, "FILE_TOO_LARGE", f"File exceeds the {limit} byte upload limit"
            )
    result = await service.upload_member_media(
        member, data=bytes(data), original_name=file.filename
    )
    if not result.created:
        response.status_code = 200
    return media_to_response(result.media)
