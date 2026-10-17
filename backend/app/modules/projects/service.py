"""Projects service: CRUD, slug handling, media/client reference validation,
strict public-visibility (published only) rules."""

from __future__ import annotations

from pymongo.errors import DuplicateKeyError

from app.core.bson import serialize_for_mongo
from app.core.errors import AppError
from app.core.slugs import slugify, validate_slug
from app.models.client import Client
from app.models.project import Project, ProjectStatus
from app.modules.clients import repository as clients_repository
from app.modules.projects import repository
from app.modules.projects.schemas import (
    ClientPublicRef,
    ClientRef,
    ProjectCreate,
    ProjectUpdate,
)
from app.services.references import require_client_exists, require_media_exist


async def _generate_unique_slug(name: str) -> str:
    base = slugify(name)
    if not base:
        raise AppError(
            422,
            "INVALID_SLUG",
            "Cannot generate a slug from this name; provide a slug explicitly",
        )
    candidate = base
    counter = 2
    while await repository.find_by_slug(candidate) is not None:
        candidate = f"{base}-{counter}"
        counter += 1
    return candidate


async def _validate_media(client_id: str | None, gallery: list[str]) -> None:
    media_ids = [client_id, *gallery]
    await require_media_exist([media_id for media_id in media_ids if media_id])


async def create_project(payload: ProjectCreate) -> Project:
    data = serialize_for_mongo(payload.model_dump(exclude_unset=True))
    await _validate_media(data.get("thumbnail_media_id"), data.get("gallery_media_ids", []))
    await require_client_exists(data.get("client_id"))

    slug = data.get("slug")
    explicit = bool(slug)
    if explicit:
        slug = validate_slug(slug)
        if await repository.find_by_slug(slug) is not None:
            raise AppError(409, "SLUG_TAKEN", "A project with this slug already exists")
    else:
        slug = await _generate_unique_slug(data["name"])

    try:
        insert_data = {key: value for key, value in data.items() if key not in ("name", "slug")}
        return await repository.insert(name=data["name"], slug=slug, **insert_data)
    except DuplicateKeyError:
        raise AppError(409, "SLUG_TAKEN", "A project with this slug already exists")


async def get_project(project_id: str) -> Project:
    project = await repository.find_by_id(project_id)
    if project is None:
        raise AppError(404, "PROJECT_NOT_FOUND", "Project was not found")
    return project


async def update_project(project_id: str, payload: ProjectUpdate) -> Project:
    existing = await get_project(project_id)
    data = serialize_for_mongo(payload.model_dump(exclude_unset=True))

    media_to_validate = []
    if "thumbnail_media_id" in data:
        media_to_validate.append(data.get("thumbnail_media_id"))
    if "gallery_media_ids" in data:
        media_to_validate.extend(data.get("gallery_media_ids") or [])
    await require_media_exist([m for m in media_to_validate if m])

    if "client_id" in data:
        await require_client_exists(data.get("client_id"))

    if "slug" in data:
        new_slug = validate_slug(data["slug"])
        if new_slug != existing.slug:
            other = await repository.find_by_slug(new_slug)
            if other is not None and other.id != project_id:
                raise AppError(409, "SLUG_TAKEN", "A project with this slug already exists")
        data["slug"] = new_slug

    fields = {key: value for key, value in data.items() if value is not None}
    for key in ("thumbnail_media_id", "client_id", "live_url", "github_url",
                "category", "description", "completion_date"):
        if key in data and data[key] is None:
            fields[key] = None

    updated = await repository.update(project_id, fields)
    if updated is None:
        raise AppError(404, "PROJECT_NOT_FOUND", "Project was not found")
    return updated


async def delete_project(project_id: str) -> None:
    await get_project(project_id)
    await repository.delete_by_id(project_id)


async def list_projects(
    *, page: int, page_size: int, query: dict, sort: list[tuple]
) -> tuple[list[Project], int]:
    return await repository.list_projects(
        query=query, sort=sort, skip=(page - 1) * page_size, limit=page_size
    )


async def _client_map(client_ids: list[str]) -> dict[str, Client]:
    return await clients_repository.find_many_by_ids(client_ids)


async def admin_client_ref(client_id: str | None) -> ClientRef | None:
    if not client_id:
        return None
    client = await clients_repository.find_by_id(client_id)
    if client is None:
        return None
    return ClientRef(id=client.id, slug=client.slug, name=client.name)


def _public_client_ref(client: Client) -> ClientPublicRef:
    return ClientPublicRef(slug=client.slug, name=client.name)


async def resolve_client_refs(projects: list[Project]) -> dict[str, ClientPublicRef | None]:
    ids = {project.client_id for project in projects if project.client_id}
    clients = await _client_map(list(ids))
    return {
        project.id: (
            _public_client_ref(clients[project.client_id])
            if project.client_id and project.client_id in clients
            else None
        )
        for project in projects
    }


async def get_public_project_by_slug(slug: str) -> tuple[Project, ClientPublicRef | None]:
    project = await repository.find_by_slug(slug)
    if project is None or project.status != ProjectStatus.PUBLISHED:
        raise AppError(404, "PROJECT_NOT_FOUND", "Project was not found")
    ref = None
    if project.client_id:
        client = await clients_repository.find_by_id(project.client_id)
        ref = _public_client_ref(client) if client else None
    return project, ref


async def list_public_projects(
    *,
    page: int,
    page_size: int,
    category: str | None,
    project_type: str | None,
    featured: bool | None,
    sort: list[tuple],
) -> tuple[list[Project], dict[str, ClientPublicRef | None], int]:
    query: dict = {"status": ProjectStatus.PUBLISHED.value}
    if category:
        query["category"] = category
    if project_type:
        query["project_type"] = project_type
    if featured is not None:
        query["featured"] = featured
    projects, total = await repository.list_projects(
        query=query, sort=sort, skip=(page - 1) * page_size, limit=page_size
    )
    refs = await resolve_client_refs(projects)
    return projects, refs, total