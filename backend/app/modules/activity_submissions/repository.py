"""Data access for the `activity_submissions` collection (no business rules here).

Individual participation only: the unique (activity_id, member_id) pair for
deliverables is the atomic guard that keeps exactly one deliverable per student
per activity, while progress updates may be filed many times.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorCollection
from pymongo import ReturnDocument
from pymongo.errors import DuplicateKeyError  # noqa: F401  (re-exported for callers)

from app.db.mongo import get_mongo
from app.models.activity_submission import (
    ActivitySubmission,
    ActivitySubmissionKind,
    ActivitySubmissionReviewEntry,
    ActivitySubmissionRevision,
    ActivitySubmissionStatus,
)

COLLECTION = "activity_submissions"


def _collection() -> AsyncIOMotorCollection:
    return get_mongo().database[COLLECTION]


def _to_submission(doc: dict) -> ActivitySubmission:
    return ActivitySubmission(
        id=str(doc["_id"]),
        activity_id=doc["activity_id"],
        activity_slug=doc["activity_slug"],
        activity_title=doc["activity_title"],
        activity_type=doc.get("activity_type", "programme"),
        member_id=doc["member_id"],
        member_readable_id=doc["member_readable_id"],
        kind=ActivitySubmissionKind(
            doc.get("kind", ActivitySubmissionKind.PROGRESS_UPDATE.value)
        ),
        title=doc.get("title"),
        description=doc["description"],
        repository_url=doc.get("repository_url"),
        demo_url=doc.get("demo_url"),
        evidence_links=doc.get("evidence_links") or [],
        attachment_media_ids=doc.get("attachment_media_ids") or [],
        status=ActivitySubmissionStatus(
            doc.get("status", ActivitySubmissionStatus.PENDING.value)
        ),
        version=doc.get("version", 0),
        client_request_id=doc.get("client_request_id"),
        submitted_at=doc["submitted_at"],
        updated_at=doc["updated_at"],
        reviewed_at=doc.get("reviewed_at"),
        reviewed_by=doc.get("reviewed_by"),
        review_feedback=doc.get("review_feedback"),
        review_history=[
            ActivitySubmissionReviewEntry(**entry)
            for entry in (doc.get("review_history") or [])
        ],
        revisions=[
            ActivitySubmissionRevision(**revision)
            for revision in (doc.get("revisions") or [])
        ],
    )


async def insert_submission(
    *,
    activity_id: str,
    activity_slug: str,
    activity_title: str,
    activity_type: str,
    member_id: str,
    member_readable_id: str,
    kind: str,
    title: str | None,
    description: str,
    repository_url: str | None,
    demo_url: str | None,
    evidence_links: list[str],
    attachment_media_ids: list[str],
    client_request_id: str | None,
) -> ActivitySubmission:
    """Insert one individual submission.

    Raises `DuplicateKeyError` when a deliverable already exists for the same
    (activity, member) or for the same (member, client_request_id).
    """
    now = datetime.now(timezone.utc)
    doc = {
        "activity_id": activity_id,
        "activity_slug": activity_slug,
        "activity_title": activity_title,
        "activity_type": activity_type,
        "member_id": member_id,
        "member_readable_id": member_readable_id,
        "kind": kind,
        "title": title,
        "description": description,
        "repository_url": repository_url,
        "demo_url": demo_url,
        "evidence_links": evidence_links,
        "attachment_media_ids": attachment_media_ids,
        "status": ActivitySubmissionStatus.PENDING.value,
        "version": 0,
        "client_request_id": client_request_id,
        "submitted_at": now,
        "updated_at": now,
        "reviewed_at": None,
        "reviewed_by": None,
        "review_feedback": None,
        "review_history": [],
        "revisions": [],
    }
    result = await _collection().insert_one(doc)
    doc["_id"] = result.inserted_id
    return _to_submission(doc)


async def find_by_id(submission_id: str) -> ActivitySubmission | None:
    if not ObjectId.is_valid(submission_id):
        return None
    doc = await _collection().find_one({"_id": ObjectId(submission_id)})
    return _to_submission(doc) if doc else None


async def find_deliverable(
    activity_id: str, member_id: str
) -> ActivitySubmission | None:
    """The member's single deliverable for one activity (if any)."""
    doc = await _collection().find_one(
        {
            "activity_id": activity_id,
            "member_id": member_id,
            "kind": ActivitySubmissionKind.DELIVERABLE.value,
        }
    )
    return _to_submission(doc) if doc else None


async def find_by_client_request(
    member_id: str, client_request_id: str
) -> ActivitySubmission | None:
    if not client_request_id:
        return None
    doc = await _collection().find_one(
        {"member_id": member_id, "client_request_id": client_request_id}
    )
    return _to_submission(doc) if doc else None


async def update_submission(
    submission_id: str,
    fields: dict[str, Any],
    *,
    review_entry: dict | None = None,
    revision: dict | None = None,
) -> ActivitySubmission | None:
    """Apply an already-validated set of fields.

    `review_entry` is *appended* to the review history (earlier entries are
    never replaced) and `revision` is *appended* to the revision list.
    """
    if not ObjectId.is_valid(submission_id):
        return None
    update: dict = {
        "$set": {**fields, "updated_at": datetime.now(timezone.utc)}
    }
    if review_entry is not None:
        update["$push"] = {"review_history": review_entry}
    if revision is not None:
        update["$push"] = {"revisions": revision}
    doc = await _collection().find_one_and_update(
        {"_id": ObjectId(submission_id)}, update, return_document=ReturnDocument.AFTER
    )
    return _to_submission(doc) if doc else None


async def list_by_activity(
    *,
    activity_id: str,
    page: int,
    page_size: int,
    status: str | None = None,
    kind: str | None = None,
    member_id: str | None = None,
) -> tuple[list[ActivitySubmission], int]:
    query: dict[str, Any] = {}
    if activity_id:
        query["activity_id"] = activity_id
    if status:
        query["status"] = status
    if kind:
        query["kind"] = kind
    if member_id:
        query["member_id"] = member_id
    collection = _collection()
    total = await collection.count_documents(query)
    cursor = (
        collection.find(query)
        .sort([("submitted_at", -1)])
        .skip((page - 1) * page_size)
        .limit(page_size)
    )
    docs = await cursor.to_list(length=page_size)
    return [_to_submission(doc) for doc in docs], total


async def list_by_member(
    *, member_id: str, page: int, page_size: int
) -> tuple[list[ActivitySubmission], int]:
    query: dict[str, Any] = {"member_id": member_id}
    collection = _collection()
    total = await collection.count_documents(query)
    cursor = (
        collection.find(query)
        .sort([("submitted_at", -1)])
        .skip((page - 1) * page_size)
        .limit(page_size)
    )
    docs = await cursor.to_list(length=page_size)
    return [_to_submission(doc) for doc in docs], total


async def list_by_member_and_activity(
    *, member_id: str, activity_id: str, kind: str | None = None
) -> list[ActivitySubmission]:
    query: dict[str, Any] = {"member_id": member_id, "activity_id": activity_id}
    if kind:
        query["kind"] = kind
    cursor = _collection().find(query).sort([("submitted_at", -1)])
    return [_to_submission(doc) async for doc in cursor]


async def status_counts_by_member(
    *, member_id: str
) -> dict[str, dict[str, int]]:
    """Return {activity_id: {total, pending, changes_requested, approved,
    rejected}} for one member in a single aggregation."""
    pipeline = [
        {"$match": {"member_id": member_id}},
        {
            "$group": {
                "_id": "$activity_id",
                "total": {"$sum": 1},
                "pending": {
                    "$sum": {
                        "$cond": [
                            {
                                "$eq": [
                                    "$status",
                                    ActivitySubmissionStatus.PENDING.value,
                                ]
                            },
                            1,
                            0,
                        ]
                    }
                },
                "changes_requested": {
                    "$sum": {
                        "$cond": [
                            {
                                "$eq": [
                                    "$status",
                                    ActivitySubmissionStatus.CHANGES_REQUESTED.value,
                                ]
                            },
                            1,
                            0,
                        ]
                    }
                },
                "approved": {
                    "$sum": {
                        "$cond": [
                            {
                                "$eq": [
                                    "$status",
                                    ActivitySubmissionStatus.APPROVED.value,
                                ]
                            },
                            1,
                            0,
                        ]
                    }
                },
                "rejected": {
                    "$sum": {
                        "$cond": [
                            {
                                "$eq": [
                                    "$status",
                                    ActivitySubmissionStatus.REJECTED.value,
                                ]
                            },
                            1,
                            0,
                        ]
                    }
                },
            }
        },
    ]
    out: dict[str, dict[str, int]] = {}
    async for row in _collection().aggregate(pipeline):
        out[row["_id"]] = {
            "total": int(row.get("total", 0)),
            "pending": int(row.get("pending", 0)),
            "changes_requested": int(row.get("changes_requested", 0)),
            "approved": int(row.get("approved", 0)),
            "rejected": int(row.get("rejected", 0)),
        }
    return out
