"""Public projects API — published projects only, no authentication.

Draft and archived projects are never returned; unpublished projects cannot be
retrieved by slug either (they 404). Internal Mongo ids are not exposed.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query

from app.deps.maintenance import require_public_site_available

from app.core.pagination import MAX_PAGE_SIZE, page_count, resolve_sort
from app.models.project import ProjectStatus, ProjectType
from app.modules.projects import service
from app.modules.projects.schemas import (
    ProjectPublicListResponse,
    ProjectPublicResponse,
)

router = APIRouter(
    prefix="/public/projects",
    tags=["public"],
    dependencies=[Depends(require_public_site_available)],
)

_SORTABLE = {"display_order", "created_at", "completion_date", "name"}


def _sort_pair(field: str, order: str) -> list[tuple]:
    name, direction = resolve_sort(field=field, order=order, allowed=_SORTABLE, default="display_order")
    secondary: tuple = ("created_at", 1) if name != "created_at" else ("name", 1)
    return [(name, direction), secondary]


def _public(project, ref) -> ProjectPublicResponse:
    return ProjectPublicResponse(
        slug=project.slug,
        name=project.name,
        thumbnail_media_id=project.thumbnail_media_id,
        gallery_media_ids=project.gallery_media_ids,
        description=project.description,
        client=ref,
        category=project.category,
        technologies=project.technologies,
        live_url=project.live_url,
        github_url=project.github_url,
        project_type=project.project_type,
        featured=project.featured,
        display_order=project.display_order,
        completion_date=project.completion_date,
    )


@router.get(
    "",
    response_model=ProjectPublicListResponse,
    summary="List published projects",
)
async def list_public_projects(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=MAX_PAGE_SIZE),
    category: str | None = Query(None, max_length=100),
    project_type: ProjectType | None = Query(None),
    featured: bool | None = Query(None),
    sort: str = Query("display_order"),
    order: str = Query("asc"),
) -> ProjectPublicListResponse:
    projects, refs, total = await service.list_public_projects(
        page=page, page_size=page_size,
        category=category,
        project_type=project_type.value if project_type else None,
        featured=featured,
        sort=_sort_pair(sort, order),
    )
    return ProjectPublicListResponse(
        items=[_public(project, refs[project.id]) for project in projects],
        total=total, page=page, page_size=page_size, pages=page_count(total, page_size),
    )


@router.get(
    "/{slug}",
    response_model=ProjectPublicResponse,
    summary="Get a published project by slug",
)
async def get_public_project(slug: str) -> ProjectPublicResponse:
    project, ref = await service.get_public_project_by_slug(slug)
    return _public(project, ref)