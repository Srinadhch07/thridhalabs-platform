"""Data access for the `branding` singleton collection."""

from __future__ import annotations

from motor.motor_asyncio import AsyncIOMotorCollection

from app.db.mongo import get_mongo
from app.models.branding import SINGLETON_KEY, Branding

COLLECTION = "branding"


def _collection() -> AsyncIOMotorCollection:
    return get_mongo().database[COLLECTION]


def _to_branding(doc: dict) -> Branding:
    return Branding(
        id=str(doc["_id"]),
        singleton=doc.get("singleton", SINGLETON_KEY),
        colors=doc["colors"],
        mode=doc.get("mode", "light"),
        theme_preset=doc.get("theme_preset"),
        media=doc.get("media", {}),
        created_at=doc["created_at"],
        updated_at=doc["updated_at"],
    )


async def get() -> Branding | None:
    doc = await _collection().find_one({"singleton": SINGLETON_KEY})
    return _to_branding(doc) if doc else None


async def upsert(body: dict) -> Branding:
    doc = {"singleton": SINGLETON_KEY, **body}
    await _collection().update_one(
        {"singleton": SINGLETON_KEY}, {"$set": doc}, upsert=True
    )
    stored = await _collection().find_one({"singleton": SINGLETON_KEY})
    assert stored is not None
    return _to_branding(stored)