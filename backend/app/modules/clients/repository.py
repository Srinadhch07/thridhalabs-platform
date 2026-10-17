"""Data access for the `clients` collection (no business rules here)."""

from __future__ import annotations

from datetime import datetime, timezone

from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorCollection

from app.db.mongo import get_mongo
from app.models.client import Client

COLLECTION = "clients"


def _collection() -> AsyncIOMotorCollection:
    return get_mongo().database[COLLECTION]


def _to_client(doc: dict) -> Client:
    return Client(
        id=str(doc["_id"]),
        name=doc["name"],
        slug=doc["slug"],
        logo_media_id=doc.get("logo_media_id"),
        featured_image_media_id=doc.get("featured_image_media_id"),
        description=doc.get("description", ""),
        website=doc.get("website"),
        industry=doc.get("industry"),
        category=doc.get("category"),
        featured=doc.get("featured", False),
        display_order=doc.get("display_order", 0),
        created_at=doc["created_at"],
        updated_at=doc["updated_at"],
    )


async def insert(*, name: str, slug: str, **fields) -> Client:
    now = datetime.now(timezone.utc)
    doc = {
        "name": name,
        "slug": slug,
        "logo_media_id": fields.get("logo_media_id"),
        "featured_image_media_id": fields.get("featured_image_media_id"),
        "description": fields.get("description", ""),
        "website": fields.get("website"),
        "industry": fields.get("industry"),
        "category": fields.get("category"),
        "featured": fields.get("featured", False),
        "display_order": fields.get("display_order", 0),
        "created_at": now,
        "updated_at": now,
    }
    result = await _collection().insert_one(doc)
    doc["_id"] = result.inserted_id
    return _to_client(doc)


async def find_by_id(client_id: str) -> Client | None:
    if not ObjectId.is_valid(client_id):
        return None
    doc = await _collection().find_one({"_id": ObjectId(client_id)})
    return _to_client(doc) if doc else None


async def find_by_slug(slug: str) -> Client | None:
    doc = await _collection().find_one({"slug": slug})
    return _to_client(doc) if doc else None


async def find_many_by_ids(ids: list[str]) -> dict[str, Client]:
    valid = [ObjectId(client_id) for client_id in ids if ObjectId.is_valid(client_id)]
    if not valid:
        return {}
    found: dict[str, Client] = {}
    cursor = _collection().find({"_id": {"$in": valid}})
    async for doc in cursor:
        found[str(doc["_id"])] = _to_client(doc)
    return found


async def update(client_id: str, fields: dict, *, now: datetime | None = None) -> Client | None:
    if not ObjectId.is_valid(client_id):
        return None
    update = dict(fields)
    update["updated_at"] = now or datetime.now(timezone.utc)
    result = await _collection().update_one(
        {"_id": ObjectId(client_id)}, {"$set": update}
    )
    if result.matched_count == 0:
        return None
    return await find_by_id(client_id)


async def delete_by_id(client_id: str) -> bool:
    if not ObjectId.is_valid(client_id):
        return False
    result = await _collection().delete_one({"_id": ObjectId(client_id)})
    return result.deleted_count > 0


async def list_clients(
    *,
    query: dict,
    sort: list[tuple],
    skip: int,
    limit: int,
) -> tuple[list[Client], int]:
    cursor = _collection().find(query).sort(sort).skip(skip).limit(limit)
    items = [ _to_client(doc) async for doc in cursor ]
    total = await _collection().count_documents(query)
    return items, total