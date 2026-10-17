"""Public activities API — published activities (and cancelled detail pages).

Drafts and archived activities are never returned. A cancelled activity is not
listed (never promoted) but remains reachable by slug so visitors see it clearly
marked as cancelled. Internal ids and stored brief object keys are never exposed.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query, Response

from app.core.pagination import MAX_PAGE_SIZE, page_count, resolve_sort
from app.deps.maintenance import require_public_site_available
from app.models.activity import ActivityType
from app.modules.activities import service
from app.modules.activities.schemas import (
    ActivityPublicListResponse,
    ActivityPublicResponse,
)

router = APIRouter(
    prefix="/public/activities",
    tags=["public"],
    dependencies=[Depends(require_public_site_available)],
)

_SORTABLE = {"display_order", "start_date", "end_date", "title"}


def _sort_pair(field: str, order: str) -> list[tuple]:
    name, direction = resolve_sort(
        field=field, order=order, allowed=_SORTABLE, default="display_order"
    )
    secondary: tuple = ("created_at", 1) if name != "created_at" else ("title", 1)
    return [(name, direction), secondary]


@router.get(
    "",
    response_model=ActivityPublicListResponse,
    summary="List published activities",
)
async def list_public_activities(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=MAX_PAGE_SIZE),
    activity_type: ActivityType | None = Query(None),
    featured: bool | None = Query(None),
    sort: str = Query("display_order"),
    order: str = Query("asc"),
) -> ActivityPublicListResponse:
    activities, total = await service.list_public(
        page=page,
        page_size=page_size,
        activity_type=activity_type.value if activity_type else None,
        featured=featured,
        sort=_sort_pair(sort, order),
    )
    return ActivityPublicListResponse(
        items=[service.to_public_response(a) for a in activities],
        total=total,
        page=page,
        page_size=page_size,
        pages=page_count(total, page_size),
    )


@router.get(
    "/{slug}",
    response_model=ActivityPublicResponse,
    summary="Get a published activity by slug",
)
async def get_public_activity(slug: str) -> ActivityPublicResponse:
    activity = await service.get_public_by_slug(slug)
    return service.to_public_response(activity)


@router.get(
    "/{slug}/brief",
    responses={
        404: {"description": "Activity or brief not found"},
    },
    summary="Download the activity's PDF brief",
)
async def download_public_brief(slug: str) -> Response:
    activity = await service.get_public_by_slug(slug)
    data, filename, mime = await service.read_brief_file(activity)
    return Response(
        content=data,
        media_type=mime,
        headers={
            "Content-Disposition": f'inline; filename="{filename}"',
            "Cache-Control": "public, max-age=300",
        },
    )
