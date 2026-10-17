"""Admin testimonials API: full CRUD with pagination/filters/sorting."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query

from app.core.pagination import MAX_PAGE_SIZE, page_count, resolve_sort
from app.deps.auth import get_active_admin, require_role
from app.deps.csrf import require_csrf
from app.models.admin import Admin
from app.models.testimonial import TestimonialStatus
from app.modules.auth.schemas import StatusResponse
from app.modules.testimonials import service
from app.modules.testimonials.schemas import (
    TestimonialAdminResponse,
    TestimonialCreate,
    TestimonialListResponse,
    TestimonialUpdate,
)

router = APIRouter(prefix="/testimonials", tags=["testimonials"])

_SORTABLE = {"display_order", "created_at", "date", "person_name"}

_ERROR_RESPONSES = {
    400: {"description": "Invalid media or client reference"},
    401: {"description": "Authentication required"},
    403: {"description": "CSRF failure, disabled account or insufficient role"},
    404: {"description": "Testimonial not found"},
    422: {"description": "Validation failure"},
}


def _sort_pair(field: str, order: str) -> list[tuple]:
    name, direction = resolve_sort(field=field, order=order, allowed=_SORTABLE, default="display_order")
    secondary: tuple = ("created_at", 1) if name != "created_at" else ("person_name", 1)
    return [(name, direction), secondary]


@router.post(
    "",
    response_model=TestimonialAdminResponse,
    status_code=201,
    dependencies=[Depends(require_csrf)],
    responses=_ERROR_RESPONSES,
    summary="Create a testimonial",
)
async def create_testimonial(
    payload: TestimonialCreate,
    admin: Admin = Depends(require_role("editor")),
) -> TestimonialAdminResponse:
    item = await service.create_testimonial(payload)
    ref = await service.admin_client_ref(item.client_id)
    return _admin(item, ref)


@router.get(
    "",
    response_model=TestimonialListResponse,
    responses=_ERROR_RESPONSES,
    summary="List testimonials (paginated)",
)
async def list_testimonials(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=MAX_PAGE_SIZE),
    sort: str = Query("display_order"),
    order: str = Query("asc"),
    published: bool | None = Query(None),
    featured: bool | None = Query(None),
    status: TestimonialStatus | None = Query(None),
    client_id: str | None = Query(None),
    admin: Admin = Depends(get_active_admin),
) -> TestimonialListResponse:
    query: dict = {}
    if published is not None:
        query["published"] = published
    if featured is not None:
        query["featured"] = featured
    if status is not None:
        query["status"] = status.value
    if client_id:
        query["client_id"] = client_id
    items, total = await service.list_testimonials(
        page=page, page_size=page_size, query=query, sort=_sort_pair(sort, order)
    )
    enriched = []
    for item in items:
        ref = await service.admin_client_ref(item.client_id)
        enriched.append(_admin(item, ref))
    return TestimonialListResponse(
        items=enriched, total=total, page=page, page_size=page_size,
        pages=page_count(total, page_size),
    )


@router.get(
    "/{testimonial_id}",
    response_model=TestimonialAdminResponse,
    responses=_ERROR_RESPONSES,
    summary="Get a testimonial",
)
async def get_testimonial(
    testimonial_id: str, admin: Admin = Depends(get_active_admin)
) -> TestimonialAdminResponse:
    item = await service.get_testimonial(testimonial_id)
    ref = await service.admin_client_ref(item.client_id)
    return _admin(item, ref)


@router.patch(
    "/{testimonial_id}",
    response_model=TestimonialAdminResponse,
    dependencies=[Depends(require_csrf)],
    responses=_ERROR_RESPONSES,
    summary="Update a testimonial",
)
async def update_testimonial(
    testimonial_id: str,
    payload: TestimonialUpdate,
    admin: Admin = Depends(require_role("editor")),
) -> TestimonialAdminResponse:
    item = await service.update_testimonial(testimonial_id, payload)
    ref = await service.admin_client_ref(item.client_id)
    return _admin(item, ref)


@router.delete(
    "/{testimonial_id}",
    response_model=StatusResponse,
    dependencies=[Depends(require_csrf)],
    responses=_ERROR_RESPONSES,
    summary="Delete a testimonial",
)
async def delete_testimonial(
    testimonial_id: str, admin: Admin = Depends(require_role("admin"))
) -> StatusResponse:
    await service.delete_testimonial(testimonial_id)
    return StatusResponse()


def _admin(item, ref) -> TestimonialAdminResponse:
    return TestimonialAdminResponse(
        id=item.id,
        client_id=item.client_id,
        client=ref,
        person_name=item.person_name,
        role=item.role,
        testimonial_text=item.testimonial_text,
        profile_image_media_id=item.profile_image_media_id,
        company=item.company,
        rating=item.rating,
        featured=item.featured,
        published=item.published,
        status=item.status,
        display_order=item.display_order,
        date=item.date,
        created_at=item.created_at,
        updated_at=item.updated_at,
    )
