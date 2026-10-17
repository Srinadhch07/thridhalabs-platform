"""Admin projects API: full CRUD with pagination/filters/sorting."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query

from app.core.pagination import MAX_PAGE_SIZE, page_count, resolve_sort
from app.deps.auth import get_active_admin, require_role
from app.deps.csrf import require_csrf
from app.models.admin import Admin
from app.modules.auth.schemas import StatusResponse
from app.modules.projects import service
from app.modules.projects.schemas import (
    ProjectAdminResponse,
    ProjectCreate,
    ProjectListResponse,
    ProjectUpdate,
)

router = APIRouter(prefix="/projects", tags=["projects"])

_SORTABLE = {"display_order", "created_at", "completion_date", "name"}

_ERROR_RESPONSES = {
    400: {"description": "Invalid media or client reference"},
    401: {"description": "Authentication required"},
    403: {"description": "CSRF failure, disabled account or insufficient role"},
    404: {"description": "Project not found"},
    409: {"description": "Slug collision"},
    422: {"description": "Validation failure"},
}


def _sort_pair(field: str, order: str) -> list[tuple]:
    name, direction = resolve_sort(field=field, order=order, allowed=_SORTABLE, default="display_order")
    secondary: tuple = ("created_at", 1) if name != "created_at" else ("name", 1)
    return [(name, direction), secondary]


@router.post(
    "",
    response_model=ProjectAdminResponse,
    status_code=201,
    dependencies=[Depends(require_csrf)],
    responses=_ERROR_RESPONSES,
    summary="Create a project",
)
async def create_project(
    payload: ProjectCreate,
    admin: Admin = Depends(require_role("editor")),
) -> ProjectAdminResponse:
    project = await service.create_project(payload)
    ref = await service.admin_client_ref(project.client_id)
    return _admin(project, ref)


@router.get(
    "",
    response_model=ProjectListResponse,
    responses=_ERROR_RESPONSES,
    summary="List projects (paginated)",
)
async def list_projects(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=MAX_PAGE_SIZE),
    sort: str = Query("display_order"),
    order: str = Query("asc"),
    status: str | None = Query(None),
    category: str | None = Query(None, max_length=100),
    project_type: str | None = Query(None),
    featured: bool | None = Query(None),
    admin: Admin = Depends(get_active_admin),
) -> ProjectListResponse:
    query: dict = {}
    if status:
        query["status"] = status
    if category:
        query["category"] = category
    if project_type:
        query["project_type"] = project_type
    if featured is not None:
        query["featured"] = featured
    projects, total = await service.list_projects(
        page=page, page_size=page_size, query=query, sort=_sort_pair(sort, order)
    )
    refs = {project.id: await service.admin_client_ref(project.client_id) for project in projects}
    return ProjectListResponse(
        items=[_admin(project, refs[project.id]) for project in projects],
        total=total, page=page, page_size=page_size, pages=page_count(total, page_size),
    )


@router.get(
    "/{project_id}",
    response_model=ProjectAdminResponse,
    responses=_ERROR_RESPONSES,
    summary="Get a project",
)
async def get_project(
    project_id: str, admin: Admin = Depends(get_active_admin)
) -> ProjectAdminResponse:
    project = await service.get_project(project_id)
    ref = await service.admin_client_ref(project.client_id)
    return _admin(project, ref)


@router.patch(
    "/{project_id}",
    response_model=ProjectAdminResponse,
    dependencies=[Depends(require_csrf)],
    responses=_ERROR_RESPONSES,
    summary="Update a project",
)
async def update_project(
    project_id: str,
    payload: ProjectUpdate,
    admin: Admin = Depends(require_role("editor")),
) -> ProjectAdminResponse:
    project = await service.update_project(project_id, payload)
    ref = await service.admin_client_ref(project.client_id)
    return _admin(project, ref)


@router.delete(
    "/{project_id}",
    response_model=StatusResponse,
    dependencies=[Depends(require_csrf)],
    responses=_ERROR_RESPONSES,
    summary="Delete a project",
)
async def delete_project(
    project_id: str, admin: Admin = Depends(require_role("admin"))
) -> StatusResponse:
    await service.delete_project(project_id)
    return StatusResponse()


def _admin(project, ref) -> ProjectAdminResponse:
    return ProjectAdminResponse(
        id=project.id,
        name=project.name,
        slug=project.slug,
        thumbnail_media_id=project.thumbnail_media_id,
        gallery_media_ids=project.gallery_media_ids,
        description=project.description,
        client_id=project.client_id,
        client=ref,
        category=project.category,
        technologies=project.technologies,
        live_url=project.live_url,
        github_url=project.github_url,
        status=project.status,
        project_type=project.project_type,
        featured=project.featured,
        display_order=project.display_order,
        completion_date=project.completion_date,
        created_at=project.created_at,
        updated_at=project.updated_at,
    )