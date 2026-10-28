"""Admin-facing activity submissions API (`/admin/activity-submissions`).

Admins review individual progress updates and deliverables, leave feedback and
request revisions. Every mutation is CSRF-protected; every read requires an
active admin account.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query

from app.core.pagination import MAX_PAGE_SIZE, page_count
from app.deps.auth import get_active_admin, require_role
from app.deps.csrf import require_csrf
from app.models.admin import Admin
from app.modules.activity_submissions import service
from app.modules.activity_submissions.schemas import (
    AdminActivitySubmissionResponse,
    AdminStudentActivityResponse,
    AdminSubmissionListResponse,
    SubmissionDecisionRequest,
)

router = APIRouter(prefix="/admin/activity-submissions", tags=["admin-activity-submissions"])

_ERROR_RESPONSES = {
    401: {"description": "Authentication required"},
    403: {"description": "CSRF failure, disabled account or insufficient role"},
    404: {"description": "Submission, activity or participation not found"},
    409: {"description": "Submission is not awaiting review"},
    422: {"description": "Validation error"},
}


@router.get(
    "",
    response_model=AdminSubmissionListResponse,
    responses=_ERROR_RESPONSES,
    summary="List activity submissions (review queue)",
)
async def list_submissions(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=MAX_PAGE_SIZE),
    status: str | None = Query(None),
    kind: str | None = Query(None),
    activity_id: str | None = Query(None),
    member_id: str | None = Query(None),
    admin: Admin = Depends(get_active_admin),
) -> AdminSubmissionListResponse:
    items, total = await service.list_for_admin(
        page=page,
        page_size=page_size,
        status=status,
        kind=kind,
        activity_id=activity_id,
        member_id=member_id,
    )
    return AdminSubmissionListResponse(
        items=await service.admin_responses(items),
        total=total,
        page=page,
        page_size=page_size,
        pages=page_count(total, page_size),
    )


@router.get(
    "/activity/{activity_id}",
    response_model=AdminSubmissionListResponse,
    responses=_ERROR_RESPONSES,
    summary="List the submissions of one activity",
)
async def list_for_activity(
    activity_id: str,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=MAX_PAGE_SIZE),
    status: str | None = Query(None),
    kind: str | None = Query(None),
    admin: Admin = Depends(get_active_admin),
) -> AdminSubmissionListResponse:
    items, total = await service.list_for_admin(
        page=page,
        page_size=page_size,
        status=status,
        kind=kind,
        activity_id=activity_id,
        member_id=None,
    )
    return AdminSubmissionListResponse(
        items=await service.admin_responses(items),
        total=total,
        page=page,
        page_size=page_size,
        pages=page_count(total, page_size),
    )


@router.get(
    "/activity/{activity_id}/students/{member_id}",
    response_model=AdminStudentActivityResponse,
    responses=_ERROR_RESPONSES,
    summary="One student's individual record in an activity",
)
async def get_student_activity(
    activity_id: str,
    member_id: str,
    admin: Admin = Depends(get_active_admin),
) -> AdminStudentActivityResponse:
    return await service.get_student_activity(activity_id, member_id)


@router.get(
    "/{submission_id}",
    response_model=AdminActivitySubmissionResponse,
    responses=_ERROR_RESPONSES,
    summary="Get one activity submission",
)
async def get_submission(
    submission_id: str, admin: Admin = Depends(get_active_admin)
) -> AdminActivitySubmissionResponse:
    submission = await service.get_for_admin(submission_id)
    items = await service.admin_responses([submission])
    return items[0]


@router.post(
    "/{submission_id}/decision",
    response_model=AdminActivitySubmissionResponse,
    dependencies=[Depends(require_csrf)],
    responses=_ERROR_RESPONSES,
    summary="Approve, request changes on, or reject a submission",
)
async def decide_submission(
    submission_id: str,
    payload: SubmissionDecisionRequest,
    admin: Admin = Depends(require_role("editor")),
) -> AdminActivitySubmissionResponse:
    submission = await service.decide_submission(
        admin,
        submission_id,
        action=payload.action,
        feedback=payload.clean_feedback(),
    )
    items = await service.admin_responses([submission])
    return items[0]
