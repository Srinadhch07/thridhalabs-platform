"""Member certification-review API (`/member/certifications`).

A member applies for a review of one of their published works and tracks its
status here. All mutations require the double-submit CSRF header.
"""

from __future__ import annotations

from typing import Literal

from fastapi import APIRouter, Depends, Query

from app.core.pagination import MAX_PAGE_SIZE, page_count
from app.deps.csrf import require_member_csrf
from app.deps.member_auth import get_enabled_member
from app.models.member import Member
from app.modules.certifications import service
from app.modules.certifications.schemas import (
    CertificationApplyRequest,
    CertificationDetailResponse,
    CertificationListResponse,
)

router = APIRouter(prefix="/member/certifications", tags=["member-certifications"])

_ERROR_RESPONSES = {
    401: {"description": "Authentication required"},
    403: {"description": "CSRF failure or disabled account"},
    404: {"description": "Work or review request not found"},
    409: {"description": "Work is unpublished, or a review is already active"},
    422: {"description": "Validation error"},
}


@router.post(
    "",
    status_code=201,
    response_model=CertificationDetailResponse,
    dependencies=[Depends(require_member_csrf)],
    responses=_ERROR_RESPONSES,
    summary="Request (or resubmit) a certification review for a published work",
)
async def apply(
    payload: CertificationApplyRequest,
    member: Member = Depends(get_enabled_member),
) -> CertificationDetailResponse:
    request = await service.apply_or_resubmit(member, payload.work_id)
    return await service.build_detail(request)


@router.get(
    "",
    response_model=CertificationListResponse,
    responses=_ERROR_RESPONSES,
    summary="List the member's own certification requests (paginated)",
)
async def list_requests(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=MAX_PAGE_SIZE),
    status: Literal[
        "submitted", "under_review", "changes_requested", "approved", "rejected"
    ]
    | None = Query(None),
    member: Member = Depends(get_enabled_member),
) -> CertificationListResponse:
    requests, total = await service.list_for_member(
        member, page=page, page_size=page_size, status=status
    )
    return CertificationListResponse(
        items=await service.build_cards(requests),
        total=total,
        page=page,
        page_size=page_size,
        pages=page_count(total, page_size),
    )


@router.get(
    "/{request_id}",
    response_model=CertificationDetailResponse,
    responses=_ERROR_RESPONSES,
    summary="Get one of the member's certification requests",
)
async def get_request(
    request_id: str,
    member: Member = Depends(get_enabled_member),
) -> CertificationDetailResponse:
    request = await service.get_for_member(member, request_id)
    return await service.build_detail(request)
