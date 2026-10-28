"""Member-facing activity workspace API (`/member/activity-workspaces`).

A member may only ever reach their *own* workspace: participation is resolved
server-side from the authenticated session, never from client input. Every
mutation requires the member double-submit CSRF header.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query

from app.core.pagination import MAX_PAGE_SIZE, page_count
from app.deps.csrf import require_member_csrf
from app.deps.member_auth import get_enabled_member
from app.models.member import Member
from app.modules.activity_submissions import service
from app.modules.activity_submissions.schemas import (
    ActivitySubmissionResponse,
    ActivityWorkspaceListResponse,
    ActivityWorkspaceResponse,
    SubmissionCreateRequest,
    SubmissionListResponse,
    SubmissionUpdateRequest,
    TaskCompletionRequest,
)

router = APIRouter(
    prefix="/member/activity-workspaces", tags=["member-activity-workspaces"]
)

_ERROR_RESPONSES = {
    401: {"description": "Authentication required"},
    403: {
        "description": "CSRF failure, disabled account, or not a confirmed participant"
    },
    404: {"description": "Activity, task or submission not found"},
    409: {"description": "Duplicate submission or submission is finalised"},
    422: {"description": "Validation error (content, attachments, deliverables)"},
}


@router.get(
    "",
    response_model=ActivityWorkspaceListResponse,
    responses=_ERROR_RESPONSES,
    summary="List my programme/hackathon workspaces",
)
async def list_my_workspaces(
    member: Member = Depends(get_enabled_member),
) -> ActivityWorkspaceListResponse:
    items = await service.list_my_workspaces(member)
    return ActivityWorkspaceListResponse(items=items)


@router.get(
    "/{slug}",
    response_model=ActivityWorkspaceResponse,
    responses=_ERROR_RESPONSES,
    summary="Get one of my activity workspaces",
)
async def get_my_workspace(
    slug: str, member: Member = Depends(get_enabled_member)
) -> ActivityWorkspaceResponse:
    return await service.get_my_workspace(member, slug)


@router.patch(
    "/{slug}/tasks",
    response_model=ActivityWorkspaceResponse,
    dependencies=[Depends(require_member_csrf)],
    responses=_ERROR_RESPONSES,
    summary="Mark one of my activity tasks complete/incomplete",
)
async def set_task_completion(
    slug: str,
    payload: TaskCompletionRequest,
    member: Member = Depends(get_enabled_member),
) -> ActivityWorkspaceResponse:
    return await service.set_task_completion(
        member, slug, task_id=payload.task_id, completed=payload.completed
    )


# ---------------------------------------------------------------------------
# Submissions
# ---------------------------------------------------------------------------
submissions_router = APIRouter(
    prefix="/member/activity-submissions", tags=["member-activity-submissions"]
)


@submissions_router.post(
    "",
    status_code=201,
    response_model=ActivitySubmissionResponse,
    dependencies=[Depends(require_member_csrf)],
    responses=_ERROR_RESPONSES,
    summary="Submit a progress update or my deliverable",
)
async def create_submission(
    payload: SubmissionCreateRequest,
    member: Member = Depends(get_enabled_member),
) -> ActivitySubmissionResponse:
    submission = await service.create_submission(member, payload)
    return ActivitySubmissionResponse.from_submission(submission)


@submissions_router.get(
    "",
    response_model=SubmissionListResponse,
    responses=_ERROR_RESPONSES,
    summary="List my activity submissions",
)
async def list_my_submissions(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=MAX_PAGE_SIZE),
    member: Member = Depends(get_enabled_member),
) -> SubmissionListResponse:
    items, total = await service.list_my_submissions(
        member, page=page, page_size=page_size
    )
    return SubmissionListResponse(
        items=[ActivitySubmissionResponse.from_submission(item) for item in items],
        total=total,
        page=page,
        page_size=page_size,
        pages=page_count(total, page_size),
    )


@submissions_router.get(
    "/{submission_id}",
    response_model=ActivitySubmissionResponse,
    responses=_ERROR_RESPONSES,
    summary="Get one of my submissions",
)
async def get_submission(
    submission_id: str, member: Member = Depends(get_enabled_member)
) -> ActivitySubmissionResponse:
    submission = await service.get_my_submission(member, submission_id)
    return ActivitySubmissionResponse.from_submission(submission)


@submissions_router.patch(
    "/{submission_id}",
    response_model=ActivitySubmissionResponse,
    dependencies=[Depends(require_member_csrf)],
    responses=_ERROR_RESPONSES,
    summary="Edit and resubmit one of my submissions",
)
async def update_submission(
    submission_id: str,
    payload: SubmissionUpdateRequest,
    member: Member = Depends(get_enabled_member),
) -> ActivitySubmissionResponse:
    submission = await service.update_submission(member, submission_id, payload)
    return ActivitySubmissionResponse.from_submission(submission)
