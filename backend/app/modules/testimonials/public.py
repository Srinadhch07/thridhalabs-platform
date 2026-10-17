"""Public testimonials API — approved testimonials only, plus submission.

Visibility model (enforced here, never left to the frontend):
- approved + published + featured -> homepage AND testimonials page
- approved + published          -> testimonials page
- anything else                 -> nowhere publicly (single-item lookups 404)

Submissions always land as pending, no matter what the client sends —
moderation fields are dropped by the submit schema and the server owns the
pending state.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query

from app.core.pagination import MAX_PAGE_SIZE, page_count, resolve_sort
from app.deps.maintenance import require_public_site_available
from app.modules.testimonials import service
from app.modules.testimonials.schemas import (
    TestimonialPublicListResponse,
    TestimonialPublicResponse,
    TestimonialSubmissionResponse,
    TestimonialSubmit,
)

router = APIRouter(
    prefix="/public/testimonials",
    tags=["public"],
    dependencies=[Depends(require_public_site_available)],
)

_SORTABLE = {"display_order", "created_at", "date", "person_name"}


def _sort_pair(field: str, order: str) -> list[tuple]:
    name, direction = resolve_sort(field=field, order=order, allowed=_SORTABLE, default="display_order")
    secondary: tuple = ("created_at", 1) if name != "created_at" else ("person_name", 1)
    return [(name, direction), secondary]


def _public(item, ref) -> TestimonialPublicResponse:
    return TestimonialPublicResponse(
        id=item.id,
        person_name=item.person_name,
        role=item.role,
        testimonial_text=item.testimonial_text,
        profile_image_media_id=item.profile_image_media_id,
        company=item.company,
        rating=item.rating,
        featured=item.featured,
        display_order=item.display_order,
        date=item.date,
        client=ref,
    )


@router.get(
    "",
    response_model=TestimonialPublicListResponse,
    summary="List published testimonials",
)
async def list_public_testimonials(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=MAX_PAGE_SIZE),
    featured: bool | None = Query(None),
    sort: str = Query("display_order"),
    order: str = Query("asc"),
) -> TestimonialPublicListResponse:
    items, refs, total = await service.list_public(
        page=page, page_size=page_size, published=True,
        featured=featured, sort=_sort_pair(sort, order),
    )
    return TestimonialPublicListResponse(
        items=[_public(item, refs[item.id]) for item in items],
        total=total, page=page, page_size=page_size, pages=page_count(total, page_size),
    )


@router.get(
    "/{testimonial_id}",
    response_model=TestimonialPublicResponse,
    summary="Get a published testimonial by id",
)
async def get_public_testimonial(testimonial_id: str) -> TestimonialPublicResponse:
    item, ref = await service.get_public(testimonial_id)
    return _public(item, ref)


@router.post(
    "",
    response_model=TestimonialSubmissionResponse,
    status_code=201,
    summary="Submit a testimonial for review",
)
async def submit_public_testimonial(payload: TestimonialSubmit) -> TestimonialSubmissionResponse:
    """Accept a public submission. Always stored as pending — moderation
    fields sent by the client are ignored, so nothing appears publicly until
    an admin approves it."""
    await service.submit_testimonial(payload)
    return TestimonialSubmissionResponse(
        message="Thank you! Your testimonial has been submitted and is awaiting approval."
    )