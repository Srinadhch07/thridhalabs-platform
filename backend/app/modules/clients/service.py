"""Clients service: CRUD, slug normalization/collision handling, referential
integrity (media + delete-blocking), public visibility filtering."""

from __future__ import annotations

from datetime import datetime, timezone

from pymongo.errors import DuplicateKeyError

from app.core.errors import AppError
from app.core.slugs import slugify, validate_slug
from app.models.client import Client
from app.modules.clients import repository
from app.modules.clients.schemas import (
    ClientCreate,
    ClientProjectRef,
    ClientUpdate,
)
from app.modules.projects import repository as projects_repository
from app.modules.testimonials import repository as testimonials_repository
from app.services.references import require_media_exist


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


async def create_client(payload: ClientCreate) -> Client:
    data = payload.model_dump(exclude_unset=True)
    await require_media_exist(
        [data.get("logo_media_id"), data.get("featured_image_media_id")]
    )

    slug = data.get("slug")
    explicit = bool(slug)
    if explicit:
        slug = validate_slug(slug)
        if await repository.find_by_slug(slug) is not None:
            raise AppError(409, "SLUG_TAKEN", "A client with this slug already exists")
    else:
        slug = await _generate_unique_slug(data["name"])

    try:
        insert_data = {key: value for key, value in data.items() if key not in ("name", "slug")}
        return await repository.insert(name=data["name"], slug=slug, **insert_data)
    except DuplicateKeyError:
        # Only reachable under a race; slug collisions surface as conflicts.
        raise AppError(409, "SLUG_TAKEN", "A client with this slug already exists")


async def get_client(client_id: str) -> Client:
    client = await repository.find_by_id(client_id)
    if client is None:
        raise AppError(404, "CLIENT_NOT_FOUND", "Client was not found")
    return client


async def update_client(client_id: str, payload: ClientUpdate) -> Client:
    existing = await get_client(client_id)
    data = payload.model_dump(exclude_unset=True)

    media_fields = [
        data.get("logo_media_id"),
        data.get("featured_image_media_id"),
    ]
    await require_media_exist(media_fields)

    if "slug" in data:
        new_slug = validate_slug(data["slug"])
        if new_slug != existing.slug:
            other = await repository.find_by_slug(new_slug)
            if other is not None and other.id != client_id:
                raise AppError(409, "SLUG_TAKEN", "A client with this slug already exists")
        data["slug"] = new_slug

    fields = {key: value for key, value in data.items() if value is not None}
    # Explicit None clears optional fields on update.
    for key in ("logo_media_id", "featured_image_media_id", "description", "website",
                "industry", "category"):
        if key in data and data[key] is None:
            fields[key] = None

    updated = await repository.update(client_id, fields)
    if updated is None:
        raise AppError(404, "CLIENT_NOT_FOUND", "Client was not found")
    return updated


async def delete_client(client_id: str) -> None:
    existing = await get_client(client_id)
    projects = await projects_repository.count_by_client(existing.id)
    testimonials = await testimonials_repository.count_by_client(existing.id)
    if projects or testimonials:
        raise AppError(
            409,
            "CLIENT_IN_USE",
            f"Client cannot be deleted: referenced by {projects} project(s) and "
            f"{testimonials} testimonial(s)",
        )
    await repository.delete_by_id(client_id)


async def list_clients(
    *,
    page: int,
    page_size: int,
    query: dict,
    sort: list[tuple],
) -> tuple[list[Client], int]:
    return await repository.list_clients(
        query=query, sort=sort, skip=(page - 1) * page_size, limit=page_size
    )


async def _project_ids_by_client(client_id: str) -> list[str]:
    return await projects_repository.list_project_ids_by_client(client_id)


async def get_client_admin(client_id: str) -> tuple[Client, list[str]]:
    client = await get_client(client_id)
    ids = await _project_ids_by_client(client.id)
    return client, ids


async def get_public_client(slug: str) -> tuple[Client, list[ClientProjectRef]]:
    client = await repository.find_by_slug(slug)
    if client is None:
        raise AppError(404, "CLIENT_NOT_FOUND", "Client was not found")
    projects = await projects_repository.find_published_by_client_ids([client.id])
    refs = [
        ClientProjectRef(slug=project.slug, name=project.name)
        for project in projects
    ]
    return client, refs


async def list_public_clients(
    *,
    page: int,
    page_size: int,
    featured: bool | None,
    sort: list[tuple],
) -> tuple[list[Client], list[list[ClientProjectRef]], int]:
    query: dict = {}
    if featured is not None:
        query["featured"] = featured
    clients, total = await repository.list_clients(
        query=query, sort=sort, skip=(page - 1) * page_size, limit=page_size
    )
    all_projects = await projects_repository.find_published_by_client_ids(
        [client.id for client in clients]
    )
    by_client: dict[str, list[ClientProjectRef]] = {}
    for project in all_projects:
        by_client.setdefault(project.client_id or "", []).append(
            ClientProjectRef(slug=project.slug, name=project.name)
        )
    ref_lists = [by_client.get(client.id, []) for client in clients]
    return clients, ref_lists, total