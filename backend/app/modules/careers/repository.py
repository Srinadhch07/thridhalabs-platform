"""Data access for careers settings + opportunities (no business rules here)."""

from __future__ import annotations

from datetime import datetime, timezone

from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorCollection

from app.db.mongo import get_mongo
from app.models.careers import SINGLETON_KEY, CareersSettings, Opportunity

SETTINGS_COLLECTION = "careers_settings"
OPPORTUNITIES_COLLECTION = "careers_opportunities"


def _settings_collection() -> AsyncIOMotorCollection:
    return get_mongo().database[SETTINGS_COLLECTION]


def _opportunities_collection() -> AsyncIOMotorCollection:
    return get_mongo().database[OPPORTUNITIES_COLLECTION]


# --------------------------------------------------------------------------
# Settings singleton
# --------------------------------------------------------------------------
def _to_settings(doc: dict) -> CareersSettings:
    return CareersSettings(
        id=str(doc["_id"]),
        singleton=doc.get("singleton", SINGLETON_KEY),
        enabled=doc.get("enabled", False),
        heading=doc.get("heading", ""),
        description=doc.get("description", ""),
        application_email=doc.get("application_email"),
        application_template=doc.get("application_template"),
        created_at=doc["created_at"],
        updated_at=doc["updated_at"],
    )


async def get_settings() -> CareersSettings | None:
    doc = await _settings_collection().find_one({"singleton": SINGLETON_KEY})
    return _to_settings(doc) if doc else None


async def upsert_settings(body: dict) -> CareersSettings:
    """Create-or-replace the careers settings singleton (race-safe via the
    unique `singleton` index). Returns the fresh stored state."""
    doc = {
        "singleton": SINGLETON_KEY,
        **body,
    }
    await _settings_collection().update_one(
        {"singleton": SINGLETON_KEY}, {"$set": doc}, upsert=True
    )
    stored = await _settings_collection().find_one({"singleton": SINGLETON_KEY})
    assert stored is not None
    return _to_settings(stored)


# --------------------------------------------------------------------------
# Opportunities
# --------------------------------------------------------------------------
def _to_opportunity(doc: dict) -> Opportunity:
    return Opportunity(
        id=str(doc["_id"]),
        title=doc["title"],
        slug=doc["slug"],
        type=doc["type"],
        custom_type=doc.get("custom_type"),
        description=doc.get("description", ""),
        skills=doc.get("skills", []),
        work_mode=doc.get("work_mode"),
        application_email=doc.get("application_email"),
        status=doc["status"],
        display_order=doc.get("display_order", 0),
        created_at=doc["created_at"],
        updated_at=doc["updated_at"],
    )


async def insert_opportunity(*, title: str, slug: str, **fields) -> Opportunity:
    now = datetime.now(timezone.utc)
    doc = {
        "title": title,
        "slug": slug,
        "type": fields["type"],
        "custom_type": fields.get("custom_type"),
        "description": fields.get("description", ""),
        "skills": fields.get("skills", []),
        "work_mode": fields.get("work_mode"),
        "application_email": fields.get("application_email"),
        "status": fields.get("status", "draft"),
        "display_order": fields.get("display_order", 0),
        "created_at": now,
        "updated_at": now,
    }
    result = await _opportunities_collection().insert_one(doc)
    doc["_id"] = result.inserted_id
    return _to_opportunity(doc)


async def find_opportunity_by_id(opportunity_id: str) -> Opportunity | None:
    if not ObjectId.is_valid(opportunity_id):
        return None
    doc = await _opportunities_collection().find_one({"_id": ObjectId(opportunity_id)})
    return _to_opportunity(doc) if doc else None


async def find_opportunity_by_slug(slug: str) -> Opportunity | None:
    doc = await _opportunities_collection().find_one({"slug": slug})
    return _to_opportunity(doc) if doc else None


async def update_opportunity(
    opportunity_id: str, fields: dict, *, now: datetime | None = None
) -> Opportunity | None:
    if not ObjectId.is_valid(opportunity_id):
        return None
    update = dict(fields)
    update["updated_at"] = now or datetime.now(timezone.utc)
    result = await _opportunities_collection().update_one(
        {"_id": ObjectId(opportunity_id)}, {"$set": update}
    )
    if result.matched_count == 0:
        return None
    return await find_opportunity_by_id(opportunity_id)


async def delete_opportunity_by_id(opportunity_id: str) -> bool:
    if not ObjectId.is_valid(opportunity_id):
        return False
    result = await _opportunities_collection().delete_one({"_id": ObjectId(opportunity_id)})
    return result.deleted_count > 0


async def list_opportunities(
    *, query: dict, sort: list[tuple], skip: int, limit: int
) -> tuple[list[Opportunity], int]:
    cursor = _opportunities_collection().find(query).sort(sort).skip(skip).limit(limit)
    items = [_to_opportunity(doc) async for doc in cursor]
    total = await _opportunities_collection().count_documents(query)
    return items, total