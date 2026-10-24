"""Legal documents service."""

from __future__ import annotations

from datetime import datetime

from app.core.errors import AppError
from app.models.legal import LegalDocument, LegalSlug
from app.modules.legal import repository

SUPPORTED_SLUGS: list[LegalSlug] = ["privacy-policy", "terms-and-conditions", "cookie-policy"]


async def ensure_seed() -> None:
    await repository.ensure_seed(SUPPORTED_SLUGS)


async def list_admin() -> list[LegalDocument]:
    await ensure_seed()
    items = await repository.list_all()
    # ensure all supported exist
    existing = {i.slug for i in items}
    for s in SUPPORTED_SLUGS:
        if s not in existing:
            await repository.ensure_seed([s])
    return await repository.list_all()


async def get_admin(slug: str) -> LegalDocument:
    if slug not in SUPPORTED_SLUGS:
        raise AppError(404, "NOT_FOUND", "Legal document not found")
    await ensure_seed()
    doc = await repository.find_by_slug(slug)  # type: ignore
    if not doc:
        raise AppError(404, "NOT_FOUND", "Legal document not found")
    return doc


async def get_public(slug: str) -> LegalDocument:
    if slug not in SUPPORTED_SLUGS:
        raise AppError(404, "NOT_FOUND", "Legal document not found")
    await ensure_seed()
    doc = await repository.find_by_slug_published(slug)  # type: ignore
    if not doc:
        raise AppError(404, "NOT_FOUND", "Legal document not published")
    return doc


async def save_draft(slug: str, *, title: str | None, content_markdown: str, expected_updated_at: datetime | None = None) -> LegalDocument:
    if slug not in SUPPORTED_SLUGS:
        raise AppError(404, "NOT_FOUND", "Legal document not found")
    await ensure_seed()
    doc = await repository.save_draft(slug, title=title, content_markdown=content_markdown, expected_updated_at=expected_updated_at)  # type: ignore
    if not doc:
        raise AppError(409, "CONFLICT", "Document was modified by another user")
    return doc


async def publish(slug: str, *, title: str | None, content_markdown: str | None = None, expected_updated_at: datetime | None = None) -> LegalDocument:
    if slug not in SUPPORTED_SLUGS:
        raise AppError(404, "NOT_FOUND", "Legal document not found")
    await ensure_seed()
    doc = await repository.publish(slug, title=title, content_markdown=content_markdown, expected_updated_at=expected_updated_at)  # type: ignore
    if not doc:
        raise AppError(409, "CONFLICT", "Document was modified by another user")
    return doc
