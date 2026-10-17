"""Admin clients API: full CRUD with pagination/filters/sorting."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query

from app.core.pagination import MAX_PAGE_SIZE, page_count, resolve_sort
from app.deps.auth import get_active_admin, require_role
from app.deps.csrf import require_csrf
from app.models.admin import Admin
from app.modules.auth.schemas import StatusResponse
from app.modules.clients import service
from app.modules.clients.schemas import (
    ClientAdminResponse,
    ClientCreate,
    ClientListResponse,
    ClientUpdate,
)

router = APIRouter(prefix="/clients", tags=["clients"])

_SORTABLE = {"display_order", "created_at", "name"}

_ERROR_RESPONSES = {
    400: {"description": "Invalid media reference"},
    401: {"description": "Authentication required"},
    403: {"description": "CSRF failure, disabled account or insufficient role"},
    404: {"description": "Client not found"},
    409: {"description": "Slug collision or client in use"},
    422: {"description": "Validation failure"},
}


def _sort_pair(field: str, order: str) -> list[tuple]:
    name, direction = resolve_sort(field=field, order=order, allowed=_SORTABLE, default="display_order")
    secondary: tuple = ("created_at", 1) if name != "created_at" else ("slug", 1)
    return [(name, direction), secondary]


@router.post(
    "",
    response_model=ClientAdminResponse,
    status_code=201,
    dependencies=[Depends(require_csrf)],
    responses=_ERROR_RESPONSES,
    summary="Create a client",
)
async def create_client(
    payload: ClientCreate,
    admin: Admin = Depends(require_role("editor")),
) -> ClientAdminResponse:
    client = await service.create_client(payload)
    client, project_ids = await service.get_client_admin(client.id)
    return _admin(client, project_ids)


@router.get(
    "",
    response_model=ClientListResponse,
    responses=_ERROR_RESPONSES,
    summary="List clients (paginated)",
)
async def list_clients(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=MAX_PAGE_SIZE),
    sort: str = Query("display_order"),
    order: str = Query("asc"),
    category: str | None = Query(None, max_length=100),
    industry: str | None = Query(None, max_length=100),
    featured: bool | None = Query(None),
    admin: Admin = Depends(get_active_admin),
) -> ClientListResponse:
    query: dict = {}
    if category:
        query["category"] = category
    if industry:
        query["industry"] = industry
    if featured is not None:
        query["featured"] = featured
    items, total = await service.list_clients(
        page=page, page_size=page_size, query=query, sort=_sort_pair(sort, order)
    )
    enriched = []
    for client in items:
        _, project_ids = await service.get_client_admin(client.id)
        enriched.append(_admin(client, project_ids))
    return ClientListResponse(
        items=enriched, total=total, page=page, page_size=page_size,
        pages=page_count(total, page_size),
    )


@router.get(
    "/{client_id}",
    response_model=ClientAdminResponse,
    responses=_ERROR_RESPONSES,
    summary="Get a client",
)
async def get_client(
    client_id: str, admin: Admin = Depends(get_active_admin)
) -> ClientAdminResponse:
    client, project_ids = await service.get_client_admin(client_id)
    return _admin(client, project_ids)


@router.patch(
    "/{client_id}",
    response_model=ClientAdminResponse,
    dependencies=[Depends(require_csrf)],
    responses=_ERROR_RESPONSES,
    summary="Update a client",
)
async def update_client(
    client_id: str,
    payload: ClientUpdate,
    admin: Admin = Depends(require_role("editor")),
) -> ClientAdminResponse:
    client = await service.update_client(client_id, payload)
    _, project_ids = await service.get_client_admin(client.id)
    return _admin(client, project_ids)


@router.delete(
    "/{client_id}",
    response_model=StatusResponse,
    dependencies=[Depends(require_csrf)],
    responses=_ERROR_RESPONSES,
    summary="Delete a client (blocked while referenced)",
)
async def delete_client(
    client_id: str, admin: Admin = Depends(require_role("admin"))
) -> StatusResponse:
    await service.delete_client(client_id)
    return StatusResponse()


def _admin(client, project_ids: list[str]) -> ClientAdminResponse:
    return ClientAdminResponse(
        id=client.id,
        name=client.name,
        slug=client.slug,
        logo_media_id=client.logo_media_id,
        featured_image_media_id=client.featured_image_media_id,
        description=client.description,
        website=client.website,
        industry=client.industry,
        category=client.category,
        featured=client.featured,
        display_order=client.display_order,
        project_ids=project_ids,
        created_at=client.created_at,
        updated_at=client.updated_at,
    )