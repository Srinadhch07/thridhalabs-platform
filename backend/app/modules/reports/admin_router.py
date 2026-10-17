"""Admin progress-report review API (`/admin/reports`).

Admins review member progress reports (queue with filters + search, detail view
with author/project/role/date/content/evidence and the full prior review
history) and approve or request changes. Decisions are restricted to
admin-level roles (`require_role("admin")` → admins/owners; editors are
rejected). A member can never reach these endpoints and can never approve their
own report.
"""

from __future__ import annotations

from typing import Literal

from fastapi import APIRouter, Depends, Query

from app.core.pagination import MAX_PAGE_SIZE, page_count, resolve_sort
from app.deps.auth import get_active_admin, require_role
from app.deps.csrf import require_csrf
from app.models.admin import Admin
from app.modules.reports import service
from app.modules.reports.schemas import (
    AdminReportListResponse,
    AdminReportResponse,
    ReportDecisionRequest,
)

router = APIRouter(prefix="/admin/reports", tags=["admin-reports"])

_SORTABLE = {"submitted_at", "updated_at", "reviewed_at"}

_ERROR_RESPONSES = {
    401: {"description": "Authentication required"},
    403: {"description": "Insufficient role (admin/owner required)"},
    404: {"description": "Report not found"},
    409: {"description": "Report is not awaiting review"},
    422: {"description": "Validation error (e.g. missing required feedback)"},
}


def _sort_pair(field: str, order: str) -> list[tuple]:
    name, direction = resolve_sort(
        field=field, order=order, allowed=_SORTABLE, default="submitted_at"
    )
    secondary: tuple = ("_id", -1) if name != "submitted_at" else ("updated_at", -1)
    return [(name, direction), secondary]


@router.get(
    "",
    response_model=AdminReportListResponse,
    responses=_ERROR_RESPONSES,
    summary="List progress reports (review queue with filters + search)",
)
async def list_reports(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=MAX_PAGE_SIZE),
    status: Literal["pending", "changes_requested", "approved"] | None = Query(None),
    activity_id: str | None = Query(None, max_length=200),
    member_id: str | None = Query(None, max_length=200),
    search: str | None = Query(None, max_length=200),
    sort: str = Query("submitted_at"),
    order: str = Query("desc"),
    admin: Admin = Depends(get_active_admin),
) -> AdminReportListResponse:
    reports, total = await service.list_for_admin(
        page=page,
        page_size=page_size,
        status=status,
        activity_id=activity_id,
        member_id=member_id,
        search=search,
        sort=_sort_pair(sort, order),
    )
    return AdminReportListResponse(
        items=await service.admin_responses(reports),
        total=total,
        page=page,
        page_size=page_size,
        pages=page_count(total, page_size),
    )


@router.get(
    "/{report_id}",
    response_model=AdminReportResponse,
    responses=_ERROR_RESPONSES,
    summary="Get a report (full content + prior review history) for review",
)
async def get_report(
    report_id: str, admin: Admin = Depends(get_active_admin)
) -> AdminReportResponse:
    report = await service.get_for_admin(report_id)
    return (await service.admin_responses([report]))[0]


@router.post(
    "/{report_id}/decision",
    response_model=AdminReportResponse,
    dependencies=[Depends(require_csrf)],
    responses=_ERROR_RESPONSES,
    summary="Approve / request changes on a report (admin/owner only)",
)
async def decide(
    report_id: str,
    payload: ReportDecisionRequest,
    admin: Admin = Depends(require_role("admin")),
) -> AdminReportResponse:
    report = await service.decide_report(
        admin,
        report_id,
        action=payload.action,
        feedback=payload.clean_feedback(),
    )
    return (await service.admin_responses([report]))[0]
