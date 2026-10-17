"""Public careers API — open opportunities only, no authentication.

When careers are disabled nothing is exposed: the settings response carries only
the public `enabled` gate flag (the frontend navigation cannot hide/show
Careers without it — the same rationale as `maintenance_mode` in site settings)
and the opportunities route 404s. Internal Mongo ids, admin metadata and the
owner's email configuration are never returned.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query

from app.core.pagination import MAX_PAGE_SIZE, page_count, resolve_sort
from app.deps.maintenance import require_public_site_available
from app.modules.careers import service
from app.modules.careers.schemas import (
    CareersSettingsPublicResponse,
    OpportunityPublicListResponse,
    public_opportunity_response,
    public_settings_response,
)

router = APIRouter(
    prefix="/public/careers",
    tags=["public"],
    dependencies=[Depends(require_public_site_available)],
)

_SORTABLE = {"display_order", "created_at", "title"}


def _sort_pair(field: str, order: str) -> list[tuple]:
    name, direction = resolve_sort(field=field, order=order, allowed=_SORTABLE, default="display_order")
    secondary: tuple = ("created_at", 1) if name != "created_at" else ("title", 1)
    return [(name, direction), secondary]


@router.get(
    "/settings",
    response_model=CareersSettingsPublicResponse,
    summary="Get public careers settings",
)
async def public_careers_settings() -> CareersSettingsPublicResponse:
    settings = await service.get_settings()
    return public_settings_response(settings)


@router.get(
    "/opportunities",
    response_model=OpportunityPublicListResponse,
    summary="List open opportunities",
)
async def list_public_opportunities(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=MAX_PAGE_SIZE),
    sort: str = Query("display_order"),
    order: str = Query("asc"),
) -> OpportunityPublicListResponse:
    opportunities, settings, total = await service.list_public_opportunities(
        page=page, page_size=page_size, sort=_sort_pair(sort, order)
    )
    items = public_opportunity_response(opportunities, settings.application_email)
    return OpportunityPublicListResponse(
        items=items, total=total, page=page, page_size=page_size, pages=page_count(total, page_size)
    )