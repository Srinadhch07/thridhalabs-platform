"""Data access for the `ai_summaries` collection (no business rules here).

At most one document exists per (activity_id, member_id) — enforced by a unique
index. Generation upserts the record; publishing/unpublishing update by id.
Generation history and publication history are bounded append-only trails.
"""

from __future__ import annotations

from datetime import datetime, timezone

from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorCollection
from pymongo import ReturnDocument

from app.db.mongo import get_mongo
from app.models.ai_summary import (
    MAX_GENERATION_HISTORY,
    MAX_PUBLICATION_HISTORY,
    AiSummary,
    SummaryGenerationEntry,
    SummarySource,
    SummaryStatus,
)

COLLECTION = "ai_summaries"


def _collection() -> AsyncIOMotorCollection:
    return get_mongo().database[COLLECTION]


def _sources(doc: dict, prefix: str) -> list[SummarySource]:
    raw = doc.get(f"{prefix}_source_reports") or []
    return [SummarySource(**item) for item in raw]


def _to_summary(doc: dict) -> AiSummary:
    return AiSummary(
        id=str(doc["_id"]),
        activity_id=doc["activity_id"],
        activity_slug=doc["activity_slug"],
        activity_title=doc["activity_title"],
        member_id=doc["member_id"],
        member_readable_id=doc["member_readable_id"],
        status=SummaryStatus(doc.get("status", SummaryStatus.DRAFT.value)),
        draft_content=doc.get("draft_content"),
        draft_model=doc.get("draft_model"),
        draft_source_hash=doc.get("draft_source_hash"),
        draft_source_reports=_sources(doc, "draft"),
        draft_generated_at=doc.get("draft_generated_at"),
        draft_generated_by=doc.get("draft_generated_by"),
        draft_reviewed_at=doc.get("draft_reviewed_at"),
        published_content=doc.get("published_content"),
        published_model=doc.get("published_model"),
        published_source_hash=doc.get("published_source_hash"),
        published_source_reports=_sources(doc, "published"),
        published_at=doc.get("published_at"),
        published_by=doc.get("published_by"),
        publication_history=doc.get("publication_history") or [],
        generations=[
            SummaryGenerationEntry(**entry) for entry in (doc.get("generations") or [])
        ],
        last_error_code=doc.get("last_error_code"),
        last_error_message=doc.get("last_error_message"),
        created_at=doc["created_at"],
        updated_at=doc["updated_at"],
    )


async def find_by_id(summary_id: str) -> AiSummary | None:
    if not ObjectId.is_valid(summary_id):
        return None
    doc = await _collection().find_one({"_id": ObjectId(summary_id)})
    return _to_summary(doc) if doc else None


async def find_by_target(activity_id: str, member_id: str) -> AiSummary | None:
    doc = await _collection().find_one(
        {"activity_id": activity_id, "member_id": member_id}
    )
    return _to_summary(doc) if doc else None


async def list_summaries(
    *, query: dict, sort: list[tuple], skip: int, limit: int
) -> tuple[list[AiSummary], int]:
    collection = _collection()
    total = await collection.count_documents(query)
    cursor = collection.find(query).sort(sort).skip(skip).limit(limit)
    docs = await cursor.to_list(length=limit)
    return [_to_summary(doc) for doc in docs], total


async def upsert_generation(
    *,
    activity_id: str,
    activity_slug: str,
    activity_title: str,
    member_id: str,
    member_readable_id: str,
    sets: dict,
    generation: SummaryGenerationEntry,
) -> AiSummary:
    """Upsert by (activity, member): apply `sets` and append one generation
    entry (bounded). Never touches the published slot unless explicitly in
    `sets`."""
    now = datetime.now(timezone.utc)
    update = {
        "$set": {**sets, "updated_at": now},
        "$setOnInsert": {
            "activity_slug": activity_slug,
            "activity_title": activity_title,
            "member_readable_id": member_readable_id,
            "created_at": now,
        },
        "$push": {
            "generations": {
                "$each": [generation.model_dump()],
                "$slice": -MAX_GENERATION_HISTORY,
            }
        },
    }
    doc = await _collection().find_one_and_update(
        {"activity_id": activity_id, "member_id": member_id},
        update,
        upsert=True,
        return_document=ReturnDocument.AFTER,
    )
    assert doc is not None
    return _to_summary(doc)


async def update_summary(
    summary_id: str,
    *,
    sets: dict,
    publication_entry: dict | None = None,
) -> AiSummary | None:
    if not ObjectId.is_valid(summary_id):
        return None
    now = datetime.now(timezone.utc)
    update: dict = {"$set": {**sets, "updated_at": now}}
    if publication_entry is not None:
        update["$push"] = {
            "publication_history": {
                "$each": [publication_entry],
                "$slice": -MAX_PUBLICATION_HISTORY,
            }
        }
    doc = await _collection().find_one_and_update(
        {"_id": ObjectId(summary_id)}, update, return_document=ReturnDocument.AFTER
    )
    return _to_summary(doc) if doc else None


async def find_published_for_member(member_id: str) -> list[AiSummary]:
    """Every published summary for a member (used by the contribution history)."""
    cursor = _collection().find(
        {"member_id": member_id, "status": SummaryStatus.PUBLISHED.value}
    ).sort([("published_at", -1)])
    return [_to_summary(doc) async for doc in cursor]


async def find_many_by_targets(
    pairs: list[tuple[str, str]],
) -> dict[tuple[str, str], AiSummary]:
    """Fetch several summaries by (activity_id, member_id) in one query."""
    unique = list(dict.fromkeys(pairs))
    if not unique:
        return {}
    query = {
        "$or": [
            {"activity_id": activity_id, "member_id": member_id}
            for activity_id, member_id in unique
        ]
    }
    out: dict[tuple[str, str], AiSummary] = {}
    async for doc in _collection().find(query):
        summary = _to_summary(doc)
        out[(summary.activity_id, summary.member_id)] = summary
    return out
