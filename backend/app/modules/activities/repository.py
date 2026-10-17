"""Data access for the `activities` and `activity_participations` collections.

No business rules live here — services validate and orchestrate. All documents
are written through `serialize_for_mongo` at the service boundary so that
date-only fields become BSON-safe ISO strings in exactly one place.
"""

from __future__ import annotations

from datetime import datetime, timezone

from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorCollection
from pymongo import ReturnDocument

from app.db.mongo import get_mongo
from app.models.activity import (
    Activity,
    ActivityBriefVersion,
    ActivityParticipation,
    ActivityStatus,
    ActivityType,
    ParticipationSource,
    ParticipationStatus,
)

ACTIVITIES = "activities"
PARTICIPATIONS = "activity_participations"


def _activities() -> AsyncIOMotorCollection:
    return get_mongo().database[ACTIVITIES]


def _participations() -> AsyncIOMotorCollection:
    return get_mongo().database[PARTICIPATIONS]


def _brief(doc: dict | None) -> ActivityBriefVersion | None:
    if not doc:
        return None
    return ActivityBriefVersion(**doc)


def _to_activity(doc: dict) -> Activity:
    return Activity(
        id=str(doc["_id"]),
        title=doc["title"],
        slug=doc["slug"],
        activity_type=ActivityType(doc["activity_type"]),
        summary=doc.get("summary", ""),
        description=doc.get("description", ""),
        status=ActivityStatus(doc.get("status", ActivityStatus.DRAFT.value)),
        start_date=doc.get("start_date"),
        end_date=doc.get("end_date"),
        banner_media_id=doc.get("banner_media_id"),
        featured=doc.get("featured", False),
        display_order=doc.get("display_order", 0),
        roles_offered=doc.get("roles_offered", []),
        tags=doc.get("tags", []),
        brief=_brief(doc.get("brief")),
        brief_versions=[
            ActivityBriefVersion(**item) for item in doc.get("brief_versions", [])
        ],
        cancel_reason=doc.get("cancel_reason"),
        created_by=doc["created_by"],
        created_at=doc["created_at"],
        updated_at=doc["updated_at"],
        published_at=doc.get("published_at"),
        cancelled_at=doc.get("cancelled_at"),
        archived_at=doc.get("archived_at"),
    )


def _to_participation(doc: dict) -> ActivityParticipation:
    return ActivityParticipation(
        id=str(doc["_id"]),
        activity_id=doc["activity_id"],
        member_id=doc["member_id"],
        member_readable_id=doc["member_readable_id"],
        role=doc.get("role"),
        status=ParticipationStatus(
            doc.get("status", ParticipationStatus.INVITED.value)
        ),
        source=ParticipationSource(
            doc.get("source", ParticipationSource.INVITED.value)
        ),
        note=doc.get("note"),
        invited_at=doc.get("invited_at"),
        responded_at=doc.get("responded_at"),
        confirmed_at=doc.get("confirmed_at"),
        withdrawn_at=doc.get("withdrawn_at"),
        email_sent_at=doc.get("email_sent_at"),
        created_at=doc["created_at"],
        updated_at=doc["updated_at"],
    )


# ---------------------------------------------------------------------------
# Activities
# ---------------------------------------------------------------------------
async def insert_activity(*, title: str, slug: str, **fields) -> Activity:
    now = datetime.now(timezone.utc)
    doc = {
        "title": title,
        "slug": slug,
        "activity_type": fields["activity_type"],
        "summary": fields.get("summary", ""),
        "description": fields.get("description", ""),
        "status": fields.get("status", ActivityStatus.DRAFT.value),
        "start_date": fields.get("start_date"),
        "end_date": fields.get("end_date"),
        "banner_media_id": fields.get("banner_media_id"),
        "featured": fields.get("featured", False),
        "display_order": fields.get("display_order", 0),
        "roles_offered": fields.get("roles_offered", []),
        "tags": fields.get("tags", []),
        "brief": None,
        "brief_versions": [],
        "cancel_reason": None,
        "created_by": fields["created_by"],
        "created_at": now,
        "updated_at": now,
        "published_at": None,
        "cancelled_at": None,
        "archived_at": None,
    }
    result = await _activities().insert_one(doc)
    doc["_id"] = result.inserted_id
    return _to_activity(doc)


async def find_activity_by_id(activity_id: str) -> Activity | None:
    if not ObjectId.is_valid(activity_id):
        return None
    doc = await _activities().find_one({"_id": ObjectId(activity_id)})
    return _to_activity(doc) if doc else None


async def find_activity_by_slug(slug: str) -> Activity | None:
    doc = await _activities().find_one({"slug": slug})
    return _to_activity(doc) if doc else None


async def find_activities_by_ids(ids: list[str]) -> dict[str, Activity]:
    valid = [ObjectId(i) for i in ids if ObjectId.is_valid(i)]
    if not valid:
        return {}
    cursor = _activities().find({"_id": {"$in": valid}})
    out: dict[str, Activity] = {}
    async for doc in cursor:
        activity = _to_activity(doc)
        out[activity.id] = activity
    return out


async def search_activity_ids(pattern: str, *, limit: int = 500) -> list[str]:
    """Return internal ids of activities whose title or slug matches a
    (already-escaped) case-insensitive regex `pattern`."""
    query = {
        "$or": [
            {"title": {"$regex": pattern, "$options": "i"}},
            {"slug": {"$regex": pattern, "$options": "i"}},
        ]
    }
    cursor = _activities().find(query, {"_id": 1}).limit(limit)
    return [str(doc["_id"]) async for doc in cursor]


async def update_activity(
    activity_id: str, fields: dict, *, now: datetime | None = None
) -> Activity | None:
    if not ObjectId.is_valid(activity_id):
        return None
    update = dict(fields)
    update["updated_at"] = now or datetime.now(timezone.utc)
    result = await _activities().update_one(
        {"_id": ObjectId(activity_id)}, {"$set": update}
    )
    if result.matched_count == 0:
        return None
    return await find_activity_by_id(activity_id)


async def append_brief_version(
    activity_id: str, *, version: ActivityBriefVersion
) -> Activity | None:
    """Append an immutable brief revision and point `brief` at it."""
    if not ObjectId.is_valid(activity_id):
        return None
    doc = await _activities().find_one_and_update(
        {"_id": ObjectId(activity_id)},
        {
            "$push": {"brief_versions": version.model_dump()},
            "$set": {
                "brief": version.model_dump(),
                "updated_at": datetime.now(timezone.utc),
            },
        },
        return_document=ReturnDocument.AFTER,
    )
    return _to_activity(doc) if doc else None


async def clear_brief(activity_id: str) -> Activity | None:
    """Clear the *current* brief pointer (history is retained)."""
    if not ObjectId.is_valid(activity_id):
        return None
    doc = await _activities().find_one_and_update(
        {"_id": ObjectId(activity_id)},
        {"$set": {"brief": None, "updated_at": datetime.now(timezone.utc)}},
        return_document=ReturnDocument.AFTER,
    )
    return _to_activity(doc) if doc else None


async def delete_activity(activity_id: str) -> bool:
    if not ObjectId.is_valid(activity_id):
        return False
    result = await _activities().delete_one({"_id": ObjectId(activity_id)})
    return result.deleted_count > 0


async def list_activities(
    *, query: dict, sort: list[tuple], skip: int, limit: int
) -> tuple[list[Activity], int]:
    cursor = _activities().find(query).sort(sort).skip(skip).limit(limit)
    items = [_to_activity(doc) async for doc in cursor]
    total = await _activities().count_documents(query)
    return items, total


# ---------------------------------------------------------------------------
# Participations
# ---------------------------------------------------------------------------
async def insert_participation(**fields) -> ActivityParticipation:
    now = datetime.now(timezone.utc)
    doc = {
        "activity_id": fields["activity_id"],
        "member_id": fields["member_id"],
        "member_readable_id": fields["member_readable_id"],
        "role": fields.get("role"),
        "status": fields.get("status", ParticipationStatus.INVITED.value),
        "source": fields.get("source", ParticipationSource.INVITED.value),
        "note": fields.get("note"),
        "invited_at": fields.get("invited_at"),
        "responded_at": None,
        "confirmed_at": fields.get("confirmed_at"),
        "withdrawn_at": None,
        "email_sent_at": fields.get("email_sent_at"),
        "created_at": now,
        "updated_at": now,
    }
    result = await _participations().insert_one(doc)
    doc["_id"] = result.inserted_id
    return _to_participation(doc)


async def find_participation_by_id(
    participation_id: str,
) -> ActivityParticipation | None:
    if not ObjectId.is_valid(participation_id):
        return None
    doc = await _participations().find_one({"_id": ObjectId(participation_id)})
    return _to_participation(doc) if doc else None


async def find_participation(
    activity_id: str, member_id: str
) -> ActivityParticipation | None:
    doc = await _participations().find_one(
        {"activity_id": activity_id, "member_id": member_id}
    )
    return _to_participation(doc) if doc else None


async def update_participation(
    participation_id: str, fields: dict, *, now: datetime | None = None
) -> ActivityParticipation | None:
    if not ObjectId.is_valid(participation_id):
        return None
    update = dict(fields)
    update["updated_at"] = now or datetime.now(timezone.utc)
    doc = await _participations().find_one_and_update(
        {"_id": ObjectId(participation_id)},
        {"$set": update},
        return_document=ReturnDocument.AFTER,
    )
    return _to_participation(doc) if doc else None


async def delete_participation(participation_id: str) -> bool:
    if not ObjectId.is_valid(participation_id):
        return False
    result = await _participations().delete_one(
        {"_id": ObjectId(participation_id)}
    )
    return result.deleted_count > 0


async def delete_participations_for_activity(activity_id: str) -> int:
    """Remove all participation records for an activity (cascade on delete)."""
    result = await _participations().delete_many({"activity_id": activity_id})
    return result.deleted_count


async def list_participations(
    *, query: dict, sort: list[tuple], skip: int, limit: int
) -> tuple[list[ActivityParticipation], int]:
    cursor = _participations().find(query).sort(sort).skip(skip).limit(limit)
    items = [_to_participation(doc) async for doc in cursor]
    total = await _participations().count_documents(query)
    return items, total


async def count_participations(activity_id: str, statuses: list[str] | None = None) -> int:
    query: dict = {"activity_id": activity_id}
    if statuses:
        query["status"] = {"$in": statuses}
    return await _participations().count_documents(query)


async def participation_counts(
    activity_ids: list[str],
) -> dict[str, dict[str, int]]:
    """Return {activity_id: {status: count}} for the given activities in one
    aggregation (avoids an N+1 query for admin listings)."""
    if not activity_ids:
        return {}
    pipeline = [
        {"$match": {"activity_id": {"$in": activity_ids}}},
        {
            "$group": {
                "_id": {"activity_id": "$activity_id", "status": "$status"},
                "n": {"$sum": 1},
            }
        },
    ]
    out: dict[str, dict[str, int]] = {}
    async for row in _participations().aggregate(pipeline):
        activity_id = row["_id"]["activity_id"]
        status = row["_id"]["status"]
        out.setdefault(activity_id, {})[status] = int(row["n"])
    return out


async def list_member_participations(
    member_id: str,
) -> list[ActivityParticipation]:
    cursor = _participations().find({"member_id": member_id}).sort(
        [("created_at", -1)]
    )
    return [_to_participation(doc) async for doc in cursor]
