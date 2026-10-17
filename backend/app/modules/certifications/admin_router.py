"""Admin certification-review API (`/admin/certifications`).

Decisions are restricted to admin-level roles (`require_role("admin")` → admins
and owners; editors are rejected). Reviewers only ever see the frozen snapshot;
the live work's version is used solely to flag `changed_since_review`.
"""

from __future__ import annotations

from typing import Literal

from fastapi import APIRouter, Depends, Query

from app.core.pagination import MAX_PAGE_SIZE, page_count
from app.deps.auth import get_active_admin, require_role
from app.deps.csrf import require_csrf
from app.models.admin import Admin
from app.modules.certifications import service
from app.modules.certifications.schemas import (
    CertificationDecisionRequest,
    CertificationDetailResponse,
    CertificationListResponse,
)

router = APIRouter(prefix="/admin/certifications", tags=["admin-certifications"])

_ERROR_RESPONSES = {
    401: {"description": "Authentication required"},
    403: {"description": "Insufficient role (admin/owner required)"},
    404: {"description": "Review request not found"},
    409: {"description": "Review already decided or awaiting resubmission"},
    422: {"description": "Validation error (e.g. missing required feedback)"},
}


@router.get(
    "",
    response_model=CertificationListResponse,
    responses=_ERROR_RESPONSES,
    summary="List certification requests (paginated)",
)
async def list_requests(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=MAX_PAGE_SIZE),
    status: Literal[
        "submitted", "under_review", "changes_requested", "approved", "rejected"
    ]
    | None = Query(None),
    admin: Admin = Depends(get_active_admin),
) -> CertificationListResponse:
    requests, total = await service.admin_list(
        page=page, page_size=page_size, status=status
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
    summary="Get a certification request (frozen snapshot)",
)
async def get_request(
    request_id: str,
    admin: Admin = Depends(get_active_admin),
) -> CertificationDetailResponse:
    request = await service.admin_get(request_id)
    return await service.build_detail(request)


@router.post(
    "/{request_id}/decision",
    response_model=CertificationDetailResponse,
    dependencies=[Depends(require_csrf)],
    responses=_ERROR_RESPONSES,
    summary="Record a review decision (admin/owner only)",
)
async def decide(
    request_id: str,
    payload: CertificationDecisionRequest,
    admin: Admin = Depends(require_role("admin")),
) -> CertificationDetailResponse:
    request = await service.decide(
        admin,
        request_id,
        action=payload.action,
        feedback=payload.clean_feedback(),
        by_role=admin.role.value,
    )
    return await service.build_detail(request)
