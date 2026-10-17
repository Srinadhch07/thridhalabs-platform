"""Admin AI summaries API (`/admin/ai`).

Generation, review, publication and unpublishing of Groq-generated work
summaries. Restricted to admin-level roles (`require_role("admin")` → admins and
owners; editors are rejected). Every mutation requires the admin CSRF header.
Generation is an explicit action only — there is no scheduling or automatic
summarization.
"""

from __future__ import annotations

from typing import Literal

from fastapi import APIRouter, Depends, Query

from app.core.pagination import MAX_PAGE_SIZE, page_count, resolve_sort
from app.deps.auth import require_role
from app.deps.csrf import require_csrf
from app.models.admin import Admin
from app.modules.ai import service
from app.modules.ai.schemas import (
    AiSourceOverviewResponse,
    AiSummaryAdminResponse,
    AiSummaryListResponse,
    SummaryDraftSaveRequest,
    SummaryGenerateRequest,
)

router = APIRouter(prefix="/admin/ai", tags=["admin-ai-summaries"])

_SORTABLE = {"updated_at", "published_at", "created_at"}

_ERROR_RESPONSES = {
    401: {"description": "Authentication required"},
    403: {"description": "Insufficient role (admin/owner required) or CSRF failure"},
    404: {"description": "Project, member or summary not found"},
    409: {
        "description": "No approved reports, not configured, draft not reviewed, "
        "or sources changed"
    },
    422: {"description": "Validation failure"},
    502: {"description": "Groq provider error"},
}


def _sort_pair(field: str, order: str) -> list[tuple]:
    name, direction = resolve_sort(
        field=field, order=order, allowed=_SORTABLE, default="updated_at"
    )
    return [(name, direction), ("_id", -1)]


@router.get(
    "/sources",
    response_model=AiSourceOverviewResponse,
    responses=_ERROR_RESPONSES,
    summary="Projects + members with approved reports eligible for summarization",
)
async def list_sources(
    admin: Admin = Depends(require_role("admin")),
) -> AiSourceOverviewResponse:
    return await service.source_overview()


@router.get(
    "/summaries",
    response_model=AiSummaryListResponse,
    responses=_ERROR_RESPONSES,
    summary="List AI summaries (admin history)",
)
async def list_summaries(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=MAX_PAGE_SIZE),
    activity_id: str | None = Query(None, max_length=200),
    member_id: str | None = Query(None, max_length=200),
    status: Literal["draft", "published"] | None = Query(None),
    sort: str = Query("updated_at"),
    order: str = Query("desc"),
    admin: Admin = Depends(require_role("admin")),
) -> AiSummaryListResponse:
    summaries, total = await service.list_for_admin(
        page=page,
        page_size=page_size,
        activity_id=activity_id,
        member_id=member_id,
        status=status,
        sort=_sort_pair(sort, order),
    )
    return AiSummaryListResponse(
        items=await service.admin_responses(summaries),
        total=total,
        page=page,
        page_size=page_size,
        pages=page_count(total, page_size),
    )


@router.post(
    "/summaries/generate",
    response_model=AiSummaryAdminResponse,
    dependencies=[Depends(require_csrf)],
    responses=_ERROR_RESPONSES,
    summary="Generate (or refresh) a draft summary from approved reports",
)
async def generate_summary(
    payload: SummaryGenerateRequest,
    admin: Admin = Depends(require_role("admin")),
) -> AiSummaryAdminResponse:
    summary = await service.generate(
        admin, activity_id=payload.activity_id, member_id=payload.member_id
    )
    return (await service.admin_responses([summary]))[0]


@router.get(
    "/summaries/{summary_id}",
    response_model=AiSummaryAdminResponse,
    responses=_ERROR_RESPONSES,
    summary="Get a summary (draft + published slots, sources, history)",
)
async def get_summary(
    summary_id: str, admin: Admin = Depends(require_role("admin"))
) -> AiSummaryAdminResponse:
    summary = await service.get_for_admin(summary_id)
    return (await service.admin_responses([summary]))[0]


@router.patch(
    "/summaries/{summary_id}",
    response_model=AiSummaryAdminResponse,
    dependencies=[Depends(require_csrf)],
    responses=_ERROR_RESPONSES,
    summary="Save (review) the editable draft (does not publish)",
)
async def save_draft(
    summary_id: str,
    payload: SummaryDraftSaveRequest,
    admin: Admin = Depends(require_role("admin")),
) -> AiSummaryAdminResponse:
    summary = await service.save_draft(admin, summary_id, payload.draft_content)
    return (await service.admin_responses([summary]))[0]


@router.post(
    "/summaries/{summary_id}/publish",
    response_model=AiSummaryAdminResponse,
    dependencies=[Depends(require_csrf)],
    responses=_ERROR_RESPONSES,
    summary="Publish a reviewed draft into official contribution history",
)
async def publish_summary(
    summary_id: str, admin: Admin = Depends(require_role("admin"))
) -> AiSummaryAdminResponse:
    summary = await service.publish(admin, summary_id)
    return (await service.admin_responses([summary]))[0]


@router.post(
    "/summaries/{summary_id}/unpublish",
    response_model=AiSummaryAdminResponse,
    dependencies=[Depends(require_csrf)],
    responses=_ERROR_RESPONSES,
    summary="Unpublish a summary (returns its content to an editable draft)",
)
async def unpublish_summary(
    summary_id: str, admin: Admin = Depends(require_role("admin"))
) -> AiSummaryAdminResponse:
    summary = await service.unpublish(admin, summary_id)
    return (await service.admin_responses([summary]))[0]
