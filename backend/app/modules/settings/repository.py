"""Data access for the `settings` singleton collection."""

from __future__ import annotations

from motor.motor_asyncio import AsyncIOMotorCollection

from app.db.mongo import get_mongo
from app.models.settings import SINGLETON_KEY, SiteSettings

COLLECTION = "settings"


def _collection() -> AsyncIOMotorCollection:
    return get_mongo().database[COLLECTION]


def _to_settings(doc: dict) -> SiteSettings:
    return SiteSettings(
        id=str(doc["_id"]),
        singleton=doc.get("singleton", SINGLETON_KEY),
        general=doc["general"],
        contact=doc["contact"],
        social=doc["social"],
        footer=doc["footer"],
        seo=doc["seo"],
        analytics=doc["analytics"],
        maintenance_mode=doc.get("maintenance_mode", False),
        created_at=doc["created_at"],
        updated_at=doc["updated_at"],
    )


async def get() -> SiteSettings | None:
    doc = await _collection().find_one({"singleton": SINGLETON_KEY})
    return _to_settings(doc) if doc else None


async def upsert(body: dict) -> SiteSettings:
    """Create-or-replace the singleton document (race-safe via the unique
    `singleton` index). Returns the fresh stored state."""
    doc = {
        "singleton": SINGLETON_KEY,
        **body,
    }
    await _collection().update_one(
        {"singleton": SINGLETON_KEY}, {"$set": doc}, upsert=True
    )
    stored = await _collection().find_one({"singleton": SINGLETON_KEY})
    assert stored is not None
    return _to_settings(stored)