"""Data access for the `ai_settings` singleton collection."""

from __future__ import annotations

from motor.motor_asyncio import AsyncIOMotorCollection

from app.db.mongo import get_mongo
from app.models.ai_settings import (
    DEFAULT_MODEL,
    PROVIDER,
    SINGLETON_KEY,
    AiSettings,
)

COLLECTION = "ai_settings"


def _collection() -> AsyncIOMotorCollection:
    return get_mongo().database[COLLECTION]


def _to_settings(doc: dict) -> AiSettings:
    return AiSettings(
        id=str(doc["_id"]),
        singleton=doc.get("singleton", SINGLETON_KEY),
        provider=doc.get("provider", PROVIDER),
        model=doc.get("model", DEFAULT_MODEL),
        enabled=doc.get("enabled", True),
        api_key_encrypted=doc.get("api_key_encrypted"),
        key_fingerprint=doc.get("key_fingerprint"),
        key_hint=doc.get("key_hint"),
        key_set_at=doc.get("key_set_at"),
        key_set_by=doc.get("key_set_by"),
        last_test_at=doc.get("last_test_at"),
        last_test_ok=doc.get("last_test_ok"),
        last_test_error=doc.get("last_test_error"),
        created_at=doc["created_at"],
        updated_at=doc["updated_at"],
    )


async def get() -> AiSettings | None:
    doc = await _collection().find_one({"singleton": SINGLETON_KEY})
    return _to_settings(doc) if doc else None


async def upsert(body: dict) -> AiSettings:
    """Create-or-replace the singleton document (race-safe via the unique
    `singleton` index). Returns the fresh stored state."""
    doc = {"singleton": SINGLETON_KEY, **body}
    await _collection().update_one(
        {"singleton": SINGLETON_KEY}, {"$set": doc}, upsert=True
    )
    stored = await _collection().find_one({"singleton": SINGLETON_KEY})
    assert stored is not None
    return _to_settings(stored)
