"""Public clients API: unauthenticated listing and slug-based detail.

Only public fields are returned (no internal Mongo ids, no unpublished content);
referenced projects are published-only and keyed by slug.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query

from app.deps.maintenance import require_public_site_available

from app.core.pagination import MAX_PAGE_SIZE, page_count, resolve_sort
from app.modules.clients import service
from app.modules.clients.schemas import (
    ClientPublicListResponse,
    ClientPublicResponse,
)

router = APIRouter(
    prefix="/public/clients",
    tags=["public"],
    dependencies=[Depends(require_public_site_available)],
)

_SORTABLE = {"display_order", "name"}


def _sort_pair(field: str, order: str) -> list[tuple]:
    name, direction = resolve_sort(field=field, order=order, allowed=_SORTABLE, default="display_order")
    secondary: tuple = ("name", 1) if name != "name" else ("slug", 1)
    return [(name, direction), ("created_at", 1), secondary]


def _public(client, refs) -> ClientPublicResponse:
    return ClientPublicResponse(
        slug=client.slug,
        name=client.name,
        logo_media_id=client.logo_media_id,
        featured_image_media_id=client.featured_image_media_id,
        description=client.description,
        website=client.website,
        industry=client.industry,
        category=client.category,
        featured=client.featured,
        display_order=client.display_order,
        projects=refs,
    )


@router.get(
    "",
    response_model=ClientPublicListResponse,
    summary="List public clients",
)
async def list_public_clients(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=MAX_PAGE_SIZE),
    featured: bool | None = Query(None),
    sort: str = Query("display_order"),
    order: str = Query("asc"),
) -> ClientPublicListResponse:
    clients, ref_lists, total = await service.list_public_clients(
        page=page, page_size=page_size, featured=featured, sort=_sort_pair(sort, order)
    )
    return ClientPublicListResponse(
        items=[_public(client, refs) for client, refs in zip(clients, ref_lists)],
        total=total, page=page, page_size=page_size, pages=page_count(total, page_size),
    )


@router.get(
    "/{slug}",
    response_model=ClientPublicResponse,
    summary="Get a public client by slug",
)
async def get_public_client(slug: str) -> ClientPublicResponse:
    client, refs = await service.get_public_client(slug)
    return _public(client, refs)