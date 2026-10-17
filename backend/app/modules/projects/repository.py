"""Data access for the `projects` collection (no business rules here)."""

from __future__ import annotations

from datetime import datetime, timezone

from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorCollection

from app.db.mongo import get_mongo
from app.models.project import Project

COLLECTION = "projects"


def _collection() -> AsyncIOMotorCollection:
    return get_mongo().database[COLLECTION]


def _to_project(doc: dict) -> Project:
    return Project(
        id=str(doc["_id"]),
        name=doc["name"],
        slug=doc["slug"],
        thumbnail_media_id=doc.get("thumbnail_media_id"),
        gallery_media_ids=doc.get("gallery_media_ids", []),
        description=doc.get("description", ""),
        client_id=doc.get("client_id"),
        category=doc.get("category"),
        technologies=doc.get("technologies", []),
        live_url=doc.get("live_url"),
        github_url=doc.get("github_url"),
        status=doc["status"],
        project_type=doc["project_type"],
        featured=doc.get("featured", False),
        display_order=doc.get("display_order", 0),
        completion_date=doc.get("completion_date"),
        created_at=doc["created_at"],
        updated_at=doc["updated_at"],
    )


async def insert(*, name: str, slug: str, **fields) -> Project:
    now = datetime.now(timezone.utc)
    doc = {
        "name": name,
        "slug": slug,
        "thumbnail_media_id": fields.get("thumbnail_media_id"),
        "gallery_media_ids": fields.get("gallery_media_ids", []),
        "description": fields.get("description", ""),
        "client_id": fields.get("client_id"),
        "category": fields.get("category"),
        "technologies": fields.get("technologies", []),
        "live_url": fields.get("live_url"),
        "github_url": fields.get("github_url"),
        "status": fields.get("status", "draft"),
        "project_type": fields["project_type"],
        "featured": fields.get("featured", False),
        "display_order": fields.get("display_order", 0),
        "completion_date": fields.get("completion_date"),
        "created_at": now,
        "updated_at": now,
    }
    result = await _collection().insert_one(doc)
    doc["_id"] = result.inserted_id
    return _to_project(doc)


async def find_by_id(project_id: str) -> Project | None:
    if not ObjectId.is_valid(project_id):
        return None
    doc = await _collection().find_one({"_id": ObjectId(project_id)})
    return _to_project(doc) if doc else None


async def find_by_slug(slug: str) -> Project | None:
    doc = await _collection().find_one({"slug": slug})
    return _to_project(doc) if doc else None


async def update(project_id: str, fields: dict, *, now: datetime | None = None) -> Project | None:
    if not ObjectId.is_valid(project_id):
        return None
    update = dict(fields)
    update["updated_at"] = now or datetime.now(timezone.utc)
    result = await _collection().update_one(
        {"_id": ObjectId(project_id)}, {"$set": update}
    )
    if result.matched_count == 0:
        return None
    return await find_by_id(project_id)


async def delete_by_id(project_id: str) -> bool:
    if not ObjectId.is_valid(project_id):
        return False
    result = await _collection().delete_one({"_id": ObjectId(project_id)})
    return result.deleted_count > 0


async def list_projects(
    *, query: dict, sort: list[tuple], skip: int, limit: int
) -> tuple[list[Project], int]:
    cursor = _collection().find(query).sort(sort).skip(skip).limit(limit)
    items = [_to_project(doc) async for doc in cursor]
    total = await _collection().count_documents(query)
    return items, total


async def count_by_client(client_id: str) -> int:
    return await _collection().count_documents({"client_id": client_id})


async def list_project_ids_by_client(client_id: str) -> list[str]:
    cursor = _collection().find(
        {"client_id": client_id},
        {"_id": 1},
    ).sort([("display_order", 1), ("created_at", 1)])
    return [str(doc["_id"]) async for doc in cursor]


async def find_published_by_client_ids(client_ids: list[str]) -> list[Project]:
    if not client_ids:
        return []
    cursor = _collection().find(
        {"client_id": {"$in": client_ids}, "status": "published"}
    ).sort([("display_order", 1), ("created_at", 1)])
    return [_to_project(doc) async for doc in cursor]