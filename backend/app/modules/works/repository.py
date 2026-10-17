"""Data access for the `member_works` collection (no business rules here)."""

from __future__ import annotations

from datetime import datetime, timezone

from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorCollection
from pymongo import ReturnDocument
from pymongo.errors import DuplicateKeyError  # noqa: F401  (re-exported for callers)

from app.db.mongo import get_mongo
from app.models.project import ProjectType
from app.models.work import (
    ContentDocument,
    ExternalLink,
    MemberWork,
    WorkPublicationStatus,
    WorkVisibility,
)

COLLECTION = "member_works"


def _collection() -> AsyncIOMotorCollection:
    return get_mongo().database[COLLECTION]


def _to_work(doc: dict) -> MemberWork:
    return MemberWork(
        id=str(doc["_id"]),
        member_id=doc["member_id"],
        title=doc["title"],
        slug=doc["slug"],
        summary=doc["summary"],
        cover_media_id=doc.get("cover_media_id"),
        tags=doc.get("tags") or [],
        external_links=[
            ExternalLink(**link) for link in (doc.get("external_links") or [])
        ],
        content=ContentDocument(**(doc.get("content") or {"blocks": []})),
        visibility=WorkVisibility(doc.get("visibility", WorkVisibility.PRIVATE.value)),
        publication_status=WorkPublicationStatus(
            doc.get("publication_status", WorkPublicationStatus.DRAFT.value)
        ),
        version=doc.get("version", 0),
        created_at=doc["created_at"],
        updated_at=doc["updated_at"],
        published_at=doc.get("published_at"),
        submitted_at=doc.get("submitted_at"),
        review_feedback=doc.get("review_feedback"),
        reviewed_at=doc.get("reviewed_at"),
        reviewed_by=doc.get("reviewed_by"),
        featured_on_projects=doc.get("featured_on_projects", False),
        featured_classification=(
            ProjectType(doc["featured_classification"])
            if doc.get("featured_classification")
            else None
        ),
        featured_at=doc.get("featured_at"),
        featured_by=doc.get("featured_by"),
    )


async def find_by_id(work_id: str) -> MemberWork | None:
    if not ObjectId.is_valid(work_id):
        return None
    doc = await _collection().find_one({"_id": ObjectId(work_id)})
    return _to_work(doc) if doc else None


async def find_by_slug(member_id: str, slug: str) -> MemberWork | None:
    doc = await _collection().find_one({"member_id": member_id, "slug": slug})
    return _to_work(doc) if doc else None


async def insert_work(
    *,
    member_id: str,
    title: str,
    slug: str,
    summary: str,
    cover_media_id: str | None,
    tags: list[str],
    external_links: list[ExternalLink],
    content: ContentDocument,
    visibility: WorkVisibility,
    publication_status: WorkPublicationStatus,
    published_at: datetime | None,
) -> MemberWork:
    now = datetime.now(timezone.utc)
    doc = {
        "member_id": member_id,
        "title": title,
        "slug": slug,
        "summary": summary,
        "cover_media_id": cover_media_id,
        "tags": tags,
        "external_links": [link.model_dump() for link in external_links],
        "content": content.model_dump(),
        "visibility": visibility.value,
        "publication_status": publication_status.value,
        "version": 0,
        "created_at": now,
        "updated_at": now,
        "published_at": published_at,
    }
    result = await _collection().insert_one(doc)
    doc["_id"] = result.inserted_id
    return _to_work(doc)


async def update_work(work_id: str, fields: dict) -> MemberWork | None:
    """Apply an already-validated set of fields, bumping the version counter."""
    doc = await _collection().find_one_and_update(
        {"_id": ObjectId(work_id)},
        {
            "$set": {**fields, "updated_at": datetime.now(timezone.utc)},
            "$inc": {"version": 1},
        },
        return_document=ReturnDocument.AFTER,
    )
    return _to_work(doc) if doc else None


async def delete_by_id(work_id: str) -> bool:
    result = await _collection().delete_one({"_id": ObjectId(work_id)})
    return result.deleted_count == 1


async def list_works(
    *,
    query: dict,
    sort: list[tuple],
    skip: int,
    limit: int,
) -> tuple[list[MemberWork], int]:
    collection = _collection()
    total = await collection.count_documents(query)
    cursor = collection.find(query).sort(sort).skip(skip).limit(limit)
    docs = await cursor.to_list(length=limit)
    return [_to_work(doc) for doc in docs], total


async def find_many_by_ids(work_ids: list[str]) -> dict[str, MemberWork]:
    valid = [ObjectId(work_id) for work_id in work_ids if ObjectId.is_valid(work_id)]
    if not valid:
        return {}
    found: dict[str, MemberWork] = {}
    cursor = _collection().find({"_id": {"$in": valid}})
    async for doc in cursor:
        found[str(doc["_id"])] = _to_work(doc)
    return found