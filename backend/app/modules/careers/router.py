"""Admin careers API: settings singleton plus full opportunity CRUD."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query

from app.core.pagination import MAX_PAGE_SIZE, page_count, resolve_sort
from app.deps.auth import get_active_admin, require_role
from app.deps.csrf import require_csrf
from app.models.admin import Admin
from app.models.careers import OpportunityStatus, OpportunityType
from app.modules.auth.schemas import StatusResponse
from app.modules.careers import service
from app.modules.careers.schemas import (
    CareersSettingsAdminResponse,
    CareersSettingsUpdate,
    OpportunityAdminResponse,
    OpportunityCreate,
    OpportunityListResponse,
    OpportunityUpdate,
    admin_opportunity_response,
    admin_settings_response,
)

router = APIRouter(prefix="/careers", tags=["careers"])

_SORTABLE = {"display_order", "created_at", "title", "status", "type"}

_ERROR_RESPONSES = {
    400: {"description": "Invalid reference"},
    401: {"description": "Authentication required"},
    403: {"description": "CSRF failure, disabled account or insufficient role"},
    404: {"description": "Careers settings, opportunity or resource not found"},
    409: {"description": "Slug collision"},
    422: {"description": "Validation failure"},
}


def _sort_pair(field: str, order: str) -> list[tuple]:
    name, direction = resolve_sort(field=field, order=order, allowed=_SORTABLE, default="display_order")
    secondary: tuple = ("created_at", 1) if name != "created_at" else ("title", 1)
    return [(name, direction), secondary]


# --------------------------------------------------------------------------
# Settings
# --------------------------------------------------------------------------
@router.get(
    "",
    response_model=CareersSettingsAdminResponse,
    responses=_ERROR_RESPONSES,
    summary="Get careers settings",
)
async def get_careers_settings(admin: Admin = Depends(get_active_admin)) -> CareersSettingsAdminResponse:
    settings = await service.get_settings()
    return admin_settings_response(settings)


@router.put(
    "",
    response_model=CareersSettingsAdminResponse,
    dependencies=[Depends(require_csrf)],
    responses=_ERROR_RESPONSES,
    summary="Replace careers settings (creates the singleton on first write)",
)
async def put_careers_settings(
    payload: CareersSettingsUpdate,
    admin: Admin = Depends(require_role("editor")),
) -> CareersSettingsAdminResponse:
    settings = await service.update_settings(payload, replace=True)
    return admin_settings_response(settings)


@router.patch(
    "",
    response_model=CareersSettingsAdminResponse,
    dependencies=[Depends(require_csrf)],
    responses=_ERROR_RESPONSES,
    summary="Partially update careers settings (creates the singleton on first write)",
)
async def patch_careers_settings(
    payload: CareersSettingsUpdate,
    admin: Admin = Depends(require_role("editor")),
) -> CareersSettingsAdminResponse:
    settings = await service.update_settings(payload, replace=False)
    return admin_settings_response(settings)


# --------------------------------------------------------------------------
# Opportunities
# --------------------------------------------------------------------------
@router.post(
    "/opportunities",
    response_model=OpportunityAdminResponse,
    status_code=201,
    dependencies=[Depends(require_csrf)],
    responses=_ERROR_RESPONSES,
    summary="Create an opportunity",
)
async def create_opportunity(
    payload: OpportunityCreate,
    admin: Admin = Depends(require_role("editor")),
) -> OpportunityAdminResponse:
    opportunity = await service.create_opportunity(payload)
    return admin_opportunity_response(opportunity)


@router.get(
    "/opportunities",
    response_model=OpportunityListResponse,
    responses=_ERROR_RESPONSES,
    summary="List opportunities (paginated)",
)
async def list_opportunities(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=MAX_PAGE_SIZE),
    sort: str = Query("display_order"),
    order: str = Query("asc"),
    status: str | None = Query(None),
    type: str | None = Query(None),
    work_mode: str | None = Query(None),
    admin: Admin = Depends(get_active_admin),
) -> OpportunityListResponse:
    query: dict = {}
    if status:
        query["status"] = status
    if type:
        query["type"] = type
    if work_mode:
        query["work_mode"] = work_mode
    opportunities, total = await service.list_opportunities(
        page=page, page_size=page_size, query=query, sort=_sort_pair(sort, order)
    )
    return OpportunityListResponse(
        items=[admin_opportunity_response(item) for item in opportunities],
        total=total, page=page, page_size=page_size, pages=page_count(total, page_size),
    )


@router.get(
    "/opportunities/{opportunity_id}",
    response_model=OpportunityAdminResponse,
    responses=_ERROR_RESPONSES,
    summary="Get an opportunity",
)
async def get_opportunity(
    opportunity_id: str, admin: Admin = Depends(get_active_admin)
) -> OpportunityAdminResponse:
    opportunity = await service.get_opportunity(opportunity_id)
    return admin_opportunity_response(opportunity)


@router.patch(
    "/opportunities/{opportunity_id}",
    response_model=OpportunityAdminResponse,
    dependencies=[Depends(require_csrf)],
    responses=_ERROR_RESPONSES,
    summary="Update an opportunity",
)
async def update_opportunity(
    opportunity_id: str,
    payload: OpportunityUpdate,
    admin: Admin = Depends(require_role("editor")),
) -> OpportunityAdminResponse:
    opportunity = await service.update_opportunity(opportunity_id, payload)
    return admin_opportunity_response(opportunity)


@router.delete(
    "/opportunities/{opportunity_id}",
    response_model=StatusResponse,
    dependencies=[Depends(require_csrf)],
    responses=_ERROR_RESPONSES,
    summary="Delete an opportunity",
)
async def delete_opportunity(
    opportunity_id: str, admin: Admin = Depends(require_role("admin"))
) -> StatusResponse:
    await service.delete_opportunity(opportunity_id)
    return StatusResponse()