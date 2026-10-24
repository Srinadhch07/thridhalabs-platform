"""Data access for legal documents collection."""

from __future__ import annotations

from datetime import datetime, timezone

from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorCollection

from app.db.mongo import get_mongo
from app.models.legal import LegalDocument, LegalSlug

COLLECTION = "legal_documents"


def _collection() -> AsyncIOMotorCollection:
    return get_mongo().database[COLLECTION]


def _to_doc(doc: dict) -> LegalDocument:
    return LegalDocument(
        id=str(doc["_id"]),
        slug=doc["slug"],
        title=doc["title"],
        content_markdown=doc.get("content_markdown", ""),
        status=doc.get("status", "draft"),
        created_at=doc["created_at"],
        updated_at=doc["updated_at"],
        published_at=doc.get("published_at"),
    )


async def find_by_slug(slug: LegalSlug) -> LegalDocument | None:
    doc = await _collection().find_one({"slug": slug})
    return _to_doc(doc) if doc else None


async def find_by_slug_published(slug: LegalSlug) -> LegalDocument | None:
    doc = await _collection().find_one({"slug": slug, "status": "published"})
    return _to_doc(doc) if doc else None


async def list_all() -> list[LegalDocument]:
    cursor = _collection().find({}).sort("slug", 1)
    items = [_to_doc(d) async for d in cursor]
    return items


async def ensure_seed(slugs: list[LegalSlug]) -> None:
    now = datetime.now(timezone.utc)
    for slug in slugs:
        exists = await _collection().find_one({"slug": slug})
        if exists:
            continue
        title_map = {
            "privacy-policy": "Privacy Policy",
            "terms-and-conditions": "Terms & Conditions",
            "cookie-policy": "Cookie Policy",
        }
        await _collection().insert_one(
            {
                "slug": slug,
                "title": title_map.get(slug, slug),
                "content_markdown": "",
                "status": "draft",
                "created_at": now,
                "updated_at": now,
                "published_at": None,
            }
        )


async def save_draft(slug: LegalSlug, *, title: str | None, content_markdown: str, expected_updated_at: datetime | None = None) -> LegalDocument | None:
    now = datetime.now(timezone.utc)
    query = {"slug": slug}
    if expected_updated_at is not None:
        query["updated_at"] = expected_updated_at
    update = {"$set": {"content_markdown": content_markdown, "updated_at": now}}
    if title is not None:
        update["$set"]["title"] = title
    result = await _collection().update_one(query, update)
    if result.matched_count == 0:
        return None
    return await find_by_slug(slug)


async def publish(slug: LegalSlug, *, title: str | None, content_markdown: str | None = None, expected_updated_at: datetime | None = None) -> LegalDocument | None:
    now = datetime.now(timezone.utc)
    query = {"slug": slug}
    if expected_updated_at is not None:
        query["updated_at"] = expected_updated_at
    update_set: dict = {"status": "published", "published_at": now, "updated_at": now}
    if title is not None:
        update_set["title"] = title
    if content_markdown is not None:
        update_set["content_markdown"] = content_markdown
    result = await _collection().update_one(query, {"$set": update_set})
    if result.matched_count == 0:
        return None
    return await find_by_slug(slug)
