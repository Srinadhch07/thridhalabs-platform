"""Admin publication-review API (`/admin/works`).

Admins review works members submitted for publication (`pending_review`) and
curate the official Projects page by featuring published, public works.
Decision and featuring actions are restricted to admin-level roles
(`require_role("admin")` → admins/owners; editors are rejected).

A member can never reach these endpoints and can never approve their own work.
"""

from __future__ import annotations

from typing import Literal

from fastapi import APIRouter, Depends, Query

from app.core.pagination import MAX_PAGE_SIZE, page_count, resolve_sort
from app.deps.auth import get_active_admin, require_role
from app.deps.csrf import require_csrf
from app.models.admin import Admin
from app.modules.members import repository as members_repository
from app.modules.works import service
from app.modules.works.schemas import (
    AdminWorkCardResponse,
    AdminWorkDetailResponse,
    AdminWorkListResponse,
    WorkFeatureRequest,
    WorkReviewDecisionRequest,
)

router = APIRouter(prefix="/admin/works", tags=["admin-works"])

_SORTABLE = {"created_at", "updated_at", "submitted_at", "published_at", "title"}

_ERROR_RESPONSES = {
    401: {"description": "Authentication required"},
    403: {"description": "Insufficient role (admin/owner required)"},
    404: {"description": "Work not found"},
    409: {"description": "Work not awaiting review / not eligible to feature"},
    422: {"description": "Validation error (e.g. missing required feedback)"},
}


def _sort_pair(field: str, order: str) -> list[tuple]:
    name, direction = resolve_sort(
        field=field, order=order, allowed=_SORTABLE, default="submitted_at"
    )
    secondary: tuple = ("created_at", -1) if name != "created_at" else ("title", 1)
    return [(name, direction), secondary]


async def _member_name(member_id: str) -> str:
    member = await members_repository.find_by_id(member_id)
    if member is None:
        return member_id
    return member.full_name or member.profile.display_name or member.member_id


@router.get(
    "",
    response_model=AdminWorkListResponse,
    responses=_ERROR_RESPONSES,
    summary="List member works (review queue + featuring state)",
)
async def list_works(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=MAX_PAGE_SIZE),
    status: Literal[
        "draft",
        "pending_review",
        "changes_requested",
        "rejected",
        "published",
        "unpublished",
    ]
    | None = Query(None),
    featured: bool | None = Query(None),
    sort: str = Query("submitted_at"),
    order: str = Query("desc"),
    admin: Admin = Depends(get_active_admin),
) -> AdminWorkListResponse:
    works, total = await service.list_for_admin(
        page=page,
        page_size=page_size,
        status=status,
        featured=featured,
        sort=_sort_pair(sort, order),
    )
    names: dict[str, str] = {}
    items: list[AdminWorkCardResponse] = []
    for work in works:
        if work.member_id not in names:
            names[work.member_id] = await _member_name(work.member_id)
        items.append(
            AdminWorkCardResponse.from_work(work, member_name=names[work.member_id])
        )
    return AdminWorkListResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        pages=page_count(total, page_size),
    )


@router.get(
    "/{work_id}",
    response_model=AdminWorkDetailResponse,
    responses=_ERROR_RESPONSES,
    summary="Get a member work (full content) for review",
)
async def get_work(
    work_id: str, admin: Admin = Depends(get_active_admin)
) -> AdminWorkDetailResponse:
    work = await service.get_for_admin(work_id)
    return AdminWorkDetailResponse.from_work(
        work, member_name=await _member_name(work.member_id)
    )


@router.post(
    "/{work_id}/decision",
    response_model=AdminWorkDetailResponse,
    dependencies=[Depends(require_csrf)],
    responses=_ERROR_RESPONSES,
    summary="Approve / request changes / reject a submission (admin/owner only)",
)
async def decide(
    work_id: str,
    payload: WorkReviewDecisionRequest,
    admin: Admin = Depends(require_role("admin")),
) -> AdminWorkDetailResponse:
    work = await service.decide_publication_review(
        admin,
        work_id,
        action=payload.action,
        feedback=payload.clean_feedback(),
    )
    return AdminWorkDetailResponse.from_work(
        work, member_name=await _member_name(work.member_id)
    )


@router.post(
    "/{work_id}/feature",
    response_model=AdminWorkDetailResponse,
    dependencies=[Depends(require_csrf)],
    responses=_ERROR_RESPONSES,
    summary="Feature/unfeature a published work on the official Projects page",
)
async def feature(
    work_id: str,
    payload: WorkFeatureRequest,
    admin: Admin = Depends(require_role("admin")),
) -> AdminWorkDetailResponse:
    work = await service.set_featured(
        admin,
        work_id,
        featured=payload.featured,
        classification=payload.classification,
    )
    return AdminWorkDetailResponse.from_work(
        work, member_name=await _member_name(work.member_id)
    )
