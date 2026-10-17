"""Member work-showcase API (`/member/works`).

Owners manage their draft/published works here: create, list, edit, delete and
the explicit publish/unpublish actions. Publication is never part of a content
update, so an autosave can't publish a work by accident. All mutations require
the double-submit CSRF header; only the owning member can reach a work.
"""

from __future__ import annotations

from typing import Literal

from fastapi import APIRouter, Depends, Query

from app.core.pagination import MAX_PAGE_SIZE, page_count
from app.deps.csrf import require_member_csrf
from app.deps.member_auth import get_enabled_member
from app.models.member import Member
from app.models.work import WorkPublicationStatus
from app.modules.auth.schemas import StatusResponse
from app.modules.works import service
from app.modules.works.schemas import (
    WorkCardResponse,
    WorkCreateRequest,
    WorkListResponse,
    WorkResponse,
    WorkUpdateRequest,
)

router = APIRouter(prefix="/member/works", tags=["member-works"])

_ERROR_RESPONSES = {
    401: {"description": "Authentication required"},
    403: {"description": "CSRF failure or disabled account"},
    404: {"description": "Work not found"},
    409: {"description": "Slug conflict or an active certification review"},
    422: {"description": "Validation error (content/media/visibility)"},
}

_SORT_MAP = {
    "newest": [("created_at", -1)],
    "oldest": [("created_at", 1)],
    "title": [("title", 1)],
    "updated": [("updated_at", -1)],
}


@router.post(
    "",
    status_code=201,
    response_model=WorkResponse,
    dependencies=[Depends(require_member_csrf)],
    responses=_ERROR_RESPONSES,
    summary="Create a work (starts as a private draft)",
)
async def create_work(
    payload: WorkCreateRequest,
    member: Member = Depends(get_enabled_member),
) -> WorkResponse:
    work = await service.create_work(member, payload)
    certification = await service.get_certification_ref(work)
    return WorkResponse.from_work(
        work,
        profile_visibility=member.profile.profile_visibility,
        certification=certification,
    )


@router.get(
    "",
    response_model=WorkListResponse,
    responses=_ERROR_RESPONSES,
    summary="List the member's works (paginated)",
)
async def list_works(
    page: int = Query(1, ge=1, description="Page number (1-based)"),
    page_size: int = Query(20, ge=1, le=MAX_PAGE_SIZE, description="Items per page"),
    status: Literal[
        "draft",
        "pending_review",
        "changes_requested",
        "rejected",
        "published",
        "unpublished",
    ]
    | None = Query(None),
    sort: Literal["newest", "oldest", "title", "updated"] = Query("newest"),
    member: Member = Depends(get_enabled_member),
) -> WorkListResponse:
    works, refs, total = await service.list_for_member(
        member,
        page=page,
        page_size=page_size,
        status=status,
        sort=_SORT_MAP[sort],
    )
    return WorkListResponse(
        items=[
            WorkCardResponse.from_work(work, certification=refs[work.id])
            for work in works
        ],
        total=total,
        page=page,
        page_size=page_size,
        pages=page_count(total, page_size),
    )


@router.get(
    "/{work_id}",
    response_model=WorkResponse,
    responses=_ERROR_RESPONSES,
    summary="Get one of the member's works",
)
async def get_work(
    work_id: str,
    member: Member = Depends(get_enabled_member),
) -> WorkResponse:
    work = await service.get_for_member(member, work_id)
    certification = await service.get_certification_ref(work)
    return WorkResponse.from_work(
        work,
        profile_visibility=member.profile.profile_visibility,
        certification=certification,
    )


@router.patch(
    "/{work_id}",
    response_model=WorkResponse,
    dependencies=[Depends(require_member_csrf)],
    responses=_ERROR_RESPONSES,
    summary="Update a work's content/metadata (does not publish)",
)
async def update_work(
    work_id: str,
    payload: WorkUpdateRequest,
    member: Member = Depends(get_enabled_member),
) -> WorkResponse:
    work = await service.update_work(member, work_id, payload)
    certification = await service.get_certification_ref(work)
    return WorkResponse.from_work(
        work,
        profile_visibility=member.profile.profile_visibility,
        certification=certification,
    )


@router.delete(
    "/{work_id}",
    response_model=StatusResponse,
    dependencies=[Depends(require_member_csrf)],
    responses=_ERROR_RESPONSES,
    summary="Delete a work (blocked during an active certification review)",
)
async def delete_work(
    work_id: str,
    member: Member = Depends(get_enabled_member),
) -> StatusResponse:
    await service.delete_work(member, work_id)
    return StatusResponse()


@router.post(
    "/{work_id}/submit",
    response_model=WorkResponse,
    dependencies=[Depends(require_member_csrf)],
    responses=_ERROR_RESPONSES,
    summary="Submit a work for publication review",
)
async def submit_work_for_review(
    work_id: str,
    member: Member = Depends(get_enabled_member),
) -> WorkResponse:
    work = await service.submit_for_review(member, work_id)
    certification = await service.get_certification_ref(work)
    return WorkResponse.from_work(
        work,
        profile_visibility=member.profile.profile_visibility,
        certification=certification,
    )


@router.post(
    "/{work_id}/withdraw",
    response_model=WorkResponse,
    dependencies=[Depends(require_member_csrf)],
    responses=_ERROR_RESPONSES,
    summary="Withdraw a pending publication-review submission",
)
async def withdraw_work_submission(
    work_id: str,
    member: Member = Depends(get_enabled_member),
) -> WorkResponse:
    work = await service.withdraw_submission(member, work_id)
    certification = await service.get_certification_ref(work)
    return WorkResponse.from_work(
        work,
        profile_visibility=member.profile.profile_visibility,
        certification=certification,
    )


@router.post(
    "/{work_id}/publish",
    response_model=WorkResponse,
    dependencies=[Depends(require_member_csrf)],
    responses=_ERROR_RESPONSES,
    summary="Publish a work",
)
async def publish_work(
    work_id: str,
    member: Member = Depends(get_enabled_member),
) -> WorkResponse:
    work = await service.set_publication(
        member, work_id, WorkPublicationStatus.PUBLISHED
    )
    certification = await service.get_certification_ref(work)
    return WorkResponse.from_work(
        work,
        profile_visibility=member.profile.profile_visibility,
        certification=certification,
    )


@router.post(
    "/{work_id}/unpublish",
    response_model=WorkResponse,
    dependencies=[Depends(require_member_csrf)],
    responses=_ERROR_RESPONSES,
    summary="Unpublish a work",
)
async def unpublish_work(
    work_id: str,
    member: Member = Depends(get_enabled_member),
) -> WorkResponse:
    work = await service.set_publication(
        member, work_id, WorkPublicationStatus.UNPUBLISHED
    )
    certification = await service.get_certification_ref(work)
    return WorkResponse.from_work(
        work,
        profile_visibility=member.profile.profile_visibility,
        certification=certification,
    )
