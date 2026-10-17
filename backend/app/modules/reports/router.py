"""Member-facing progress-reports API (`/member/reports`).

A member submits short progress reports for projects they are a *confirmed*
participant of, views and edits/resubmits their own reports, sees their report
state per project, and views their official contribution history (approved
reports only). All mutations require the member double-submit CSRF header; a
member can only ever reach their own reports.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query

from app.core.pagination import MAX_PAGE_SIZE, page_count
from app.deps.csrf import require_member_csrf
from app.deps.member_auth import get_enabled_member
from app.models.member import Member
from app.modules.reports import service
from app.modules.reports.schemas import (
    ContributionHistoryResponse,
    MemberProjectListResponse,
    ReportCreateRequest,
    ReportListResponse,
    ReportResponse,
    ReportUpdateRequest,
)

router = APIRouter(prefix="/member/reports", tags=["member-reports"])

_ERROR_RESPONSES = {
    401: {"description": "Authentication required"},
    403: {
        "description": "CSRF failure, disabled account, or not a confirmed participant"
    },
    404: {"description": "Report or project not found"},
    409: {"description": "Duplicate submission or report is finalised"},
    422: {"description": "Validation error (description/evidence links)"},
}


@router.get(
    "",
    response_model=ReportListResponse,
    responses=_ERROR_RESPONSES,
    summary="List my progress reports",
)
async def list_my_reports(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=MAX_PAGE_SIZE),
    activity_id: str | None = Query(None, max_length=200),
    member: Member = Depends(get_enabled_member),
) -> ReportListResponse:
    reports, total = await service.list_my_reports(
        member, activity_id=activity_id, page=page, page_size=page_size
    )
    return ReportListResponse(
        items=await service.member_responses(reports),
        total=total,
        page=page,
        page_size=page_size,
        pages=page_count(total, page_size),
    )


@router.get(
    "/projects",
    response_model=MemberProjectListResponse,
    responses=_ERROR_RESPONSES,
    summary="List my confirmed projects with report roll-ups",
)
async def list_my_projects(
    member: Member = Depends(get_enabled_member),
) -> MemberProjectListResponse:
    items = await service.list_member_projects(member)
    return MemberProjectListResponse(items=items)


@router.get(
    "/contributions",
    response_model=ContributionHistoryResponse,
    responses=_ERROR_RESPONSES,
    summary="My official contribution history (approved reports, by project)",
)
async def contribution_history(
    member: Member = Depends(get_enabled_member),
) -> ContributionHistoryResponse:
    return await service.contribution_history(member)


@router.post(
    "",
    status_code=201,
    response_model=ReportResponse,
    dependencies=[Depends(require_member_csrf)],
    responses=_ERROR_RESPONSES,
    summary="Submit a progress report for one of my projects",
)
async def create_report(
    payload: ReportCreateRequest,
    member: Member = Depends(get_enabled_member),
) -> ReportResponse:
    report = await service.create_report(member, payload)
    return ReportResponse.from_report(report)


@router.get(
    "/{report_id}",
    response_model=ReportResponse,
    responses=_ERROR_RESPONSES,
    summary="Get one of my reports",
)
async def get_report(
    report_id: str,
    member: Member = Depends(get_enabled_member),
) -> ReportResponse:
    report = await service.get_my_report(member, report_id)
    return ReportResponse.from_report(report)


@router.patch(
    "/{report_id}",
    response_model=ReportResponse,
    dependencies=[Depends(require_member_csrf)],
    responses=_ERROR_RESPONSES,
    summary="Edit and resubmit one of my reports (pending/changes-requested)",
)
async def edit_report(
    report_id: str,
    payload: ReportUpdateRequest,
    member: Member = Depends(get_enabled_member),
) -> ReportResponse:
    report = await service.edit_report(member, report_id, payload)
    return ReportResponse.from_report(report)
