"""Admin activities API: CRUD, lifecycle, PDF briefs, invitations, participants.

Invitations and brief uploads are editor+; deletion is admin+. Every mutation is
CSRF-protected. Only `published` projects accept invitations so a link in the
email always resolves publicly.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, File, Query, Response, UploadFile

from app.core.config import get_settings
from app.core.errors import AppError
from app.core.pagination import MAX_PAGE_SIZE, page_count, resolve_sort
from app.deps.auth import get_active_admin, require_role
from app.deps.csrf import require_csrf
from app.models.admin import Admin
from app.modules.activities import service
from app.modules.activities.schemas import (
    ActivityAdminListResponse,
    ActivityAdminResponse,
    ActivityCreate,
    ActivityUpdate,
    InvitationRequest,
    InvitationResult,
    ParticipantListResponse,
    ParticipantResponse,
    ParticipantUpdateRequest,
)
from app.modules.auth.schemas import StatusResponse

router = APIRouter(prefix="/admin/activities", tags=["admin-activities"])

_SORTABLE = {"display_order", "created_at", "start_date", "end_date", "title"}

_ERROR_RESPONSES = {
    400: {"description": "Invalid media reference"},
    401: {"description": "Authentication required"},
    403: {"description": "CSRF failure, disabled account or insufficient role"},
    404: {"description": "Activity or participant not found"},
    409: {"description": "Slug collision, lifecycle or registration conflict"},
    413: {"description": "Brief exceeds the configured size limit"},
    415: {"description": "Brief is not a PDF"},
    422: {"description": "Validation failure"},
}


def _sort_pair(field: str, order: str) -> list[tuple]:
    name, direction = resolve_sort(
        field=field, order=order, allowed=_SORTABLE, default="display_order"
    )
    secondary: tuple = ("created_at", -1) if name != "created_at" else ("title", 1)
    return [(name, direction), secondary]


@router.post(
    "",
    response_model=ActivityAdminResponse,
    status_code=201,
    dependencies=[Depends(require_csrf)],
    responses=_ERROR_RESPONSES,
    summary="Create an activity",
)
async def create_activity(
    payload: ActivityCreate, admin: Admin = Depends(require_role("editor"))
) -> ActivityAdminResponse:
    activity = await service.create_activity(payload, admin_id=admin.id)
    return service.to_admin_response(activity)


@router.get(
    "",
    response_model=ActivityAdminListResponse,
    responses=_ERROR_RESPONSES,
    summary="List activities (paginated)",
)
async def list_activities(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=MAX_PAGE_SIZE),
    sort: str = Query("display_order"),
    order: str = Query("asc"),
    status: str | None = Query(None),
    activity_type: str | None = Query(None),
    featured: bool | None = Query(None),
    admin: Admin = Depends(get_active_admin),
) -> ActivityAdminListResponse:
    query: dict = {}
    if status:
        query["status"] = status
    if activity_type:
        query["activity_type"] = activity_type
    if featured is not None:
        query["featured"] = featured
    activities, counts, total = await service.list_admin(
        page=page, page_size=page_size, query=query, sort=_sort_pair(sort, order)
    )
    return ActivityAdminListResponse(
        items=[service.to_admin_response(a, counts.get(a.id)) for a in activities],
        total=total,
        page=page,
        page_size=page_size,
        pages=page_count(total, page_size),
    )


@router.get(
    "/{activity_id}",
    response_model=ActivityAdminResponse,
    responses=_ERROR_RESPONSES,
    summary="Get an activity",
)
async def get_activity(
    activity_id: str, admin: Admin = Depends(get_active_admin)
) -> ActivityAdminResponse:
    activity, counts = await service.get_admin(activity_id)
    return service.to_admin_response(activity, counts)


@router.patch(
    "/{activity_id}",
    response_model=ActivityAdminResponse,
    dependencies=[Depends(require_csrf)],
    responses=_ERROR_RESPONSES,
    summary="Update an activity (including lifecycle status)",
)
async def update_activity(
    activity_id: str,
    payload: ActivityUpdate,
    admin: Admin = Depends(require_role("editor")),
) -> ActivityAdminResponse:
    activity = await service.update_activity(activity_id, payload)
    _, counts = await service.get_admin(activity.id)
    return service.to_admin_response(activity, counts)

@router.delete(
    "/{activity_id}",
    response_model=StatusResponse,
    dependencies=[Depends(require_csrf)],
    responses=_ERROR_RESPONSES,
    summary="Delete an activity",
)
async def delete_activity(
    activity_id: str, admin: Admin = Depends(require_role("admin"))
) -> StatusResponse:
    await service.delete_activity(activity_id)
    return StatusResponse()


# ---------------------------------------------------------------------------
# PDF brief
# ---------------------------------------------------------------------------
@router.post(
    "/{activity_id}/brief",
    response_model=ActivityAdminResponse,
    dependencies=[Depends(require_csrf)],
    responses=_ERROR_RESPONSES,
    summary="Upload or replace the PDF brief (versioned)",
)
async def upload_brief(
    activity_id: str,
    file: UploadFile = File(..., description="PDF brief"),
    admin: Admin = Depends(require_role("editor")),
) -> ActivityAdminResponse:
    limit = get_settings().ACTIVITY_BRIEF_MAX_BYTES
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
    activity = await service.upload_brief(
        activity_id, admin_id=admin.id, data=bytes(data), filename=file.filename
    )
    return service.to_admin_response(activity)


@router.get(
    "/{activity_id}/brief",
    responses=_ERROR_RESPONSES,
    summary="Download the current PDF brief (admin)",
)
async def download_brief(
    activity_id: str, admin: Admin = Depends(get_active_admin)
) -> Response:
    activity = await service.get_activity(activity_id)
    data, filename, mime = await service.read_brief_file(activity)
    return Response(
        content=data,
        media_type=mime,
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "Cache-Control": "private, no-store",
        },
    )


@router.delete(
    "/{activity_id}/brief",
    response_model=ActivityAdminResponse,
    dependencies=[Depends(require_csrf)],
    responses=_ERROR_RESPONSES,
    summary="Remove the current PDF brief (history is retained)",
)
async def delete_brief(
    activity_id: str, admin: Admin = Depends(require_role("editor"))
) -> ActivityAdminResponse:
    activity = await service.remove_brief(activity_id)
    return service.to_admin_response(activity)


# ---------------------------------------------------------------------------
# Invitations + participants
# ---------------------------------------------------------------------------
@router.post(
    "/{activity_id}/invitations",
    response_model=InvitationResult,
    dependencies=[Depends(require_csrf)],
    responses=_ERROR_RESPONSES,
    summary="Invite members to a project (sends emails)",
)
async def send_invitations(
    activity_id: str,
    payload: InvitationRequest,
    admin: Admin = Depends(require_role("editor")),
) -> InvitationResult:
    return await service.send_invitations(activity_id, payload)


@router.get(
    "/{activity_id}/participants",
    response_model=ParticipantListResponse,
    responses=_ERROR_RESPONSES,
    summary="List participants (paginated)",
)
async def list_participants(
    activity_id: str,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=MAX_PAGE_SIZE),
    status: str | None = Query(None),
    admin: Admin = Depends(get_active_admin),
) -> ParticipantListResponse:
    participations, total = await service.list_participants(
        activity_id=activity_id, page=page, page_size=page_size, status=status
    )
    items = [await service.to_participant_response(p) for p in participations]
    return ParticipantListResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        pages=page_count(total, page_size),
    )


@router.patch(
    "/{activity_id}/participants/{participation_id}",
    response_model=ParticipantResponse,
    dependencies=[Depends(require_csrf)],
    responses=_ERROR_RESPONSES,
    summary="Update a participant (confirm / decline / role / note)",
)
async def update_participant(
    activity_id: str,
    participation_id: str,
    payload: ParticipantUpdateRequest,
    admin: Admin = Depends(require_role("editor")),
) -> ParticipantResponse:
    participation = await service.update_participant(
        activity_id, participation_id, payload
    )
    return await service.to_participant_response(participation)
