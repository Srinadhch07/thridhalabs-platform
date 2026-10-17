"""Careers service: settings singleton semantics, opportunity CRUD with slug
handling, and strict public-visibility rules (open only, careers enabled)."""

from __future__ import annotations

from datetime import datetime, timezone

from pymongo.errors import DuplicateKeyError

from app.core.bson import serialize_for_mongo
from app.core.errors import AppError
from app.core.slugs import slugify, validate_slug
from app.models.careers import (
    CareersSettings,
    Opportunity,
    OpportunityStatus,
    OpportunityType,
    default_careers_settings_doc,
)
from app.modules.careers import repository
from app.modules.careers.schemas import (
    CareersSettingsUpdate,
    OpportunityCreate,
    OpportunityUpdate,
)


# --------------------------------------------------------------------------
# Settings
# --------------------------------------------------------------------------
async def get_settings() -> CareersSettings:
    existing = await repository.get_settings()
    if existing is not None:
        return existing
    # Empty state is returned without persisting anything — a GET must not
    # unexpectedly create data. New installs start with careers disabled.
    base = default_careers_settings_doc()
    now = datetime.now(timezone.utc)
    return CareersSettings(id="default", created_at=now, updated_at=now, **base)


async def update_settings(payload: CareersSettingsUpdate, *, replace: bool) -> CareersSettings:
    existing = await repository.get_settings()
    if existing is None or replace:
        base = default_careers_settings_doc()
    else:
        base = existing.model_dump(exclude={"id", "created_at", "updated_at"})

    data = payload.model_dump(exclude_unset=True)
    for key in ("enabled", "heading", "description", "application_email", "application_template"):
        if key in data and data[key] is not None:
            base[key] = data[key]

    now = datetime.now(timezone.utc)
    created_at = existing.created_at if existing is not None else now
    model = CareersSettings(id="__ignored__", created_at=created_at, updated_at=now, **base)
    body = model.model_dump(exclude={"id", "singleton", "created_at", "updated_at"})
    body["updated_at"] = now
    body["created_at"] = created_at
    return await repository.upsert_settings(body)


# --------------------------------------------------------------------------
# Opportunity CRUD
# --------------------------------------------------------------------------
async def _generate_unique_slug(title: str) -> str:
    base = slugify(title)
    if not base:
        raise AppError(
            422,
            "INVALID_SLUG",
            "Cannot generate a slug from this title; provide a slug explicitly",
        )
    candidate = base
    counter = 2
    while await repository.find_opportunity_by_slug(candidate) is not None:
        candidate = f"{base}-{counter}"
        counter += 1
    return candidate


async def create_opportunity(payload: OpportunityCreate) -> Opportunity:
    data = serialize_for_mongo(payload.model_dump(exclude_unset=True))

    slug = data.get("slug")
    explicit = bool(slug)
    if explicit:
        slug = validate_slug(slug)
        if await repository.find_opportunity_by_slug(slug) is not None:
            raise AppError(409, "SLUG_TAKEN", "An opportunity with this slug already exists")
    else:
        slug = await _generate_unique_slug(data["title"])

    try:
        insert_data = {key: value for key, value in data.items() if key not in ("title", "slug")}
        return await repository.insert_opportunity(title=data["title"], slug=slug, **insert_data)
    except DuplicateKeyError:
        raise AppError(409, "SLUG_TAKEN", "An opportunity with this slug already exists")


async def get_opportunity(opportunity_id: str) -> Opportunity:
    opportunity = await repository.find_opportunity_by_id(opportunity_id)
    if opportunity is None:
        raise AppError(404, "OPPORTUNITY_NOT_FOUND", "Opportunity was not found")
    return opportunity


async def update_opportunity(opportunity_id: str, payload: OpportunityUpdate) -> Opportunity:
    existing = await get_opportunity(opportunity_id)
    data = serialize_for_mongo(payload.model_dump(exclude_unset=True))

    # Keep stored state coherent when the type stops being "Other": a leftover
    # custom label must not linger on a non-Other opportunity.
    if data.get("type") is not None and data.get("type") != OpportunityType.OTHER.value:
        data["custom_type"] = None

    if "slug" in data:
        new_slug = validate_slug(data["slug"])
        if new_slug != existing.slug:
            other = await repository.find_opportunity_by_slug(new_slug)
            if other is not None and other.id != opportunity_id:
                raise AppError(409, "SLUG_TAKEN", "An opportunity with this slug already exists")
        data["slug"] = new_slug

    fields = {key: value for key, value in data.items() if value is not None}
    for key in ("custom_type", "work_mode", "application_email", "description", "skills"):
        if key in data and data[key] is None:
            fields[key] = None

    updated = await repository.update_opportunity(opportunity_id, fields)
    if updated is None:
        raise AppError(404, "OPPORTUNITY_NOT_FOUND", "Opportunity was not found")
    return updated


async def delete_opportunity(opportunity_id: str) -> None:
    await get_opportunity(opportunity_id)
    await repository.delete_opportunity_by_id(opportunity_id)


async def list_opportunities(
    *, page: int, page_size: int, query: dict, sort: list[tuple]
) -> tuple[list[Opportunity], int]:
    return await repository.list_opportunities(
        query=query, sort=sort, skip=(page - 1) * page_size, limit=page_size
    )


# --------------------------------------------------------------------------
# Public rules
# --------------------------------------------------------------------------
async def ensure_careers_enabled() -> CareersSettings:
    """Public guard: 404 whenever careers are disabled — nothing is exposed."""
    settings = await get_settings()
    if not settings.enabled:
        raise AppError(404, "CAREERS_NOT_AVAILABLE", "Careers are not currently available")
    return settings


async def list_public_opportunities(
    *, page: int, page_size: int, sort: list[tuple]
) -> tuple[list[Opportunity], CareersSettings, int]:
    settings = await ensure_careers_enabled()
    query: dict = {"status": OpportunityStatus.OPEN.value}
    opportunities, total = await repository.list_opportunities(
        query=query, sort=sort, skip=(page - 1) * page_size, limit=page_size
    )
    return opportunities, settings, total