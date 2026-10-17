"""Data access for the `media` collection (no business rules here)."""

from __future__ import annotations

from datetime import datetime, timezone

from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorCollection
from pymongo import ASCENDING, DESCENDING

from app.db.mongo import get_mongo
from app.models.media import Media, MediaVariant

COLLECTION = "media"


def _collection() -> AsyncIOMotorCollection:
    return get_mongo().database[COLLECTION]


def _to_media(doc: dict) -> Media:
    return Media(
        id=str(doc["_id"]),
        original_name=doc["original_name"],
        format=doc["format"],
        mime_type=doc["mime_type"],
        media_type=doc["media_type"],
        size_bytes=doc["size_bytes"],
        width=doc["width"],
        height=doc["height"],
        checksum=doc["checksum"],
        storage_mode=doc["storage_mode"],
        object_key=doc["object_key"],
        variants=[MediaVariant(**variant) for variant in doc["variants"]],
        created_by=doc["created_by"],
        created_at=doc["created_at"],
        updated_at=doc["updated_at"],
    )


async def insert_media(
    *,
    original_name: str,
    format: str,
    mime_type: str,
    media_type: str,
    size_bytes: int,
    width: int,
    height: int,
    checksum: str,
    storage_mode: str,
    object_key: str,
    variants: list[MediaVariant],
    created_by: str,
) -> Media:
    now = datetime.now(timezone.utc)
    doc = {
        "original_name": original_name,
        "format": format,
        "mime_type": mime_type,
        "media_type": media_type,
        "size_bytes": size_bytes,
        "width": width,
        "height": height,
        "checksum": checksum,
        "storage_mode": storage_mode,
        "object_key": object_key,
        "variants": [variant.model_dump() for variant in variants],
        "created_by": created_by,
        "created_at": now,
        "updated_at": now,
    }
    result = await _collection().insert_one(doc)
    doc["_id"] = result.inserted_id
    return _to_media(doc)


async def find_by_id(media_id: str) -> Media | None:
    if not ObjectId.is_valid(media_id):
        return None
    doc = await _collection().find_one({"_id": ObjectId(media_id)})
    return _to_media(doc) if doc else None


async def find_many_by_id(ids: list[str]) -> dict[str, Media]:
    """Return {media_id: Media} for every referenced media record that exists.

    Invalid or missing ids simply do not appear in the result — callers compare
    against the requested set to detect broken references.
    """
    valid = [ObjectId(media_id) for media_id in ids if ObjectId.is_valid(media_id)]
    if not valid:
        return {}
    found: dict[str, Media] = {}
    cursor = _collection().find({"_id": {"$in": valid}})
    async for doc in cursor:
        found[str(doc["_id"])] = _to_media(doc)
    return found


async def find_by_checksum_and_mode(checksum: str, storage_mode: str) -> Media | None:
    doc = await _collection().find_one(
        {"checksum": checksum, "storage_mode": storage_mode}
    )
    return _to_media(doc) if doc else None


async def delete_by_id(media_id: str) -> bool:
    if not ObjectId.is_valid(media_id):
        return False
    result = await _collection().delete_one({"_id": ObjectId(media_id)})
    return result.deleted_count > 0


async def count_total() -> int:
    return await _collection().count_documents({})


async def list_media(
    *, page: int, page_size: int, newest: bool
) -> tuple[list[Media], int]:
    """Return (page of media, total count) ordered by created_at."""
    sort_dir = DESCENDING if newest else ASCENDING
    cursor = (
        _collection()
        .find({}, sort=[("created_at", sort_dir)])
        .skip((page - 1) * page_size)
        .limit(page_size)
    )
    items: list[Media] = []
    async for doc in cursor:
        items.append(_to_media(doc))
    total = await _collection().count_documents({})
    return items, total


async def list_by_creator(
    *, created_by: str, page: int, page_size: int, newest: bool = True
) -> tuple[list[Media], int]:
    """Return (page of media, total count) owned by one creator (e.g. member)."""
    sort_dir = DESCENDING if newest else ASCENDING
    cursor = (
        _collection()
        .find({"created_by": created_by}, sort=[("created_at", sort_dir)])
        .skip((page - 1) * page_size)
        .limit(page_size)
    )
    items: list[Media] = []
    async for doc in cursor:
        items.append(_to_media(doc))
    total = await _collection().count_documents({"created_by": created_by})
    return items, total