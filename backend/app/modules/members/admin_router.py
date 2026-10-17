"""Admin member-management API (`/members`).

Member records are PII, so the whole surface requires at least an `admin`
role; permanent deletion additionally requires `owner`. Members can never
reach these endpoints — and admins can never use member-only endpoints.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query

from app.core.pagination import MAX_PAGE_SIZE, page_count, resolve_sort
from app.deps.auth import require_role
from app.deps.csrf import require_csrf
from app.models.admin import Admin
from app.modules.auth.schemas import StatusResponse
from app.modules.members import service
from app.modules.members.schemas import (
    MemberAdminResponse,
    MemberCreateRequest,
    MemberListResponse,
    MemberUpdateRequest,
)

router = APIRouter(prefix="/members", tags=["members"])

_SORTABLE = {"created_at", "updated_at", "member_id", "email", "status", "last_login_at"}

_ERROR_RESPONSES = {
    400: {"description": "Invalid payload or reference"},
    401: {"description": "Authentication required"},
    403: {"description": "CSRF failure, disabled account or insufficient role"},
    404: {"description": "Member not found"},
    409: {"description": "Email already taken / onboarding already complete"},
    422: {"description": "Validation failure"},
}


def _sort_pair(field: str, order: str) -> list[tuple]:
    name, direction = resolve_sort(
        field=field, order=order, allowed=_SORTABLE, default="created_at"
    )
    secondary: tuple = ("created_at", -1) if name != "created_at" else ("email", 1)
    return [(name, direction), secondary]


@router.get(
    "",
    response_model=MemberListResponse,
    responses=_ERROR_RESPONSES,
    summary="List members (paginated)",
)
async def list_members(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=MAX_PAGE_SIZE),
    sort: str = Query("created_at"),
    order: str = Query("desc"),
    status: str | None = Query(None),
    search: str | None = Query(None, max_length=200),
    admin: Admin = Depends(require_role("admin")),
) -> MemberListResponse:
    members, total = await service.list_members(
        page=page,
        page_size=page_size,
        status=status,
        search=search,
        sort=_sort_pair(sort, order),
    )
    return MemberListResponse(
        items=[MemberAdminResponse.from_member(member) for member in members],
        total=total,
        page=page,
        page_size=page_size,
        pages=page_count(total, page_size),
    )


@router.post(
    "",
    response_model=MemberAdminResponse,
    status_code=201,
    dependencies=[Depends(require_csrf)],
    responses=_ERROR_RESPONSES,
    summary="Create a member account and send the onboarding link",
)
async def create_member(
    payload: MemberCreateRequest,
    admin: Admin = Depends(require_role("admin")),
) -> MemberAdminResponse:
    member = await service.create_member(payload, admin)
    return MemberAdminResponse.from_member(member)


@router.get(
    "/{member_id}",
    response_model=MemberAdminResponse,
    responses=_ERROR_RESPONSES,
    summary="Get a member",
)
async def get_member(
    member_id: str, admin: Admin = Depends(require_role("admin"))
) -> MemberAdminResponse:
    member = await service.get_member(member_id)
    return MemberAdminResponse.from_member(member)


@router.patch(
    "/{member_id}",
    response_model=MemberAdminResponse,
    dependencies=[Depends(require_csrf)],
    responses=_ERROR_RESPONSES,
    summary="Update a member's admin-managed fields",
)
async def update_member(
    member_id: str,
    payload: MemberUpdateRequest,
    admin: Admin = Depends(require_role("admin")),
) -> MemberAdminResponse:
    member = await service.update_member(member_id, payload)
    return MemberAdminResponse.from_member(member)


@router.post(
    "/{member_id}/resend",
    response_model=MemberAdminResponse,
    dependencies=[Depends(require_csrf)],
    responses=_ERROR_RESPONSES,
    summary="Resend the onboarding link (invalidates the previous one)",
)
async def resend_onboarding(
    member_id: str, admin: Admin = Depends(require_role("admin"))
) -> MemberAdminResponse:
    member = await service.resend_onboarding(member_id)
    return MemberAdminResponse.from_member(member)


@router.post(
    "/{member_id}/deactivate",
    response_model=MemberAdminResponse,
    dependencies=[Depends(require_csrf)],
    responses=_ERROR_RESPONSES,
    summary="Deactivate a member (revokes sessions and any setup link)",
)
async def deactivate_member(
    member_id: str, admin: Admin = Depends(require_role("admin"))
) -> MemberAdminResponse:
    member = await service.deactivate_member(member_id)
    return MemberAdminResponse.from_member(member)


@router.post(
    "/{member_id}/reactivate",
    response_model=MemberAdminResponse,
    dependencies=[Depends(require_csrf)],
    responses=_ERROR_RESPONSES,
    summary="Reactivate a member (re-issues setup if never completed)",
)
async def reactivate_member(
    member_id: str, admin: Admin = Depends(require_role("admin"))
) -> MemberAdminResponse:
    member = await service.reactivate_member(member_id)
    return MemberAdminResponse.from_member(member)


@router.delete(
    "/{member_id}",
    response_model=StatusResponse,
    dependencies=[Depends(require_csrf)],
    responses=_ERROR_RESPONSES,
    summary="Permanently delete a member (owner only)",
)
async def delete_member(
    member_id: str, admin: Admin = Depends(require_role("owner"))
) -> StatusResponse:
    await service.delete_member(member_id)
    return StatusResponse()