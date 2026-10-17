"""Data access for the `progress_reports` collection (no business rules here)."""

from __future__ import annotations

from datetime import datetime, timezone

from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorCollection
from pymongo import ReturnDocument
from pymongo.errors import DuplicateKeyError  # noqa: F401  (re-exported for callers)

from app.db.mongo import get_mongo
from app.models.progress_report import (
    ProgressReport,
    ReportReviewEntry,
    ReportStatus,
)

COLLECTION = "progress_reports"


def _collection() -> AsyncIOMotorCollection:
    return get_mongo().database[COLLECTION]


def _to_report(doc: dict) -> ProgressReport:
    return ProgressReport(
        id=str(doc["_id"]),
        activity_id=doc["activity_id"],
        activity_slug=doc["activity_slug"],
        activity_title=doc["activity_title"],
        member_id=doc["member_id"],
        member_readable_id=doc["member_readable_id"],
        role=doc.get("role"),
        description=doc["description"],
        evidence_links=doc.get("evidence_links") or [],
        status=ReportStatus(doc.get("status", ReportStatus.PENDING.value)),
        version=doc.get("version", 0),
        client_request_id=doc.get("client_request_id"),
        submitted_at=doc["submitted_at"],
        updated_at=doc["updated_at"],
        reviewed_at=doc.get("reviewed_at"),
        reviewed_by=doc.get("reviewed_by"),
        review_feedback=doc.get("review_feedback"),
        review_history=[
            ReportReviewEntry(**entry) for entry in (doc.get("review_history") or [])
        ],
    )


async def insert_report(
    *,
    activity_id: str,
    activity_slug: str,
    activity_title: str,
    member_id: str,
    member_readable_id: str,
    role: str | None,
    description: str,
    evidence_links: list[str],
    client_request_id: str | None,
) -> ProgressReport:
    """Insert a new report. Raises `DuplicateKeyError` when a report already
    exists for the same (member, client_request_id) — the atomic guard that
    makes a retried/double-clicked submission idempotent."""
    now = datetime.now(timezone.utc)
    doc = {
        "activity_id": activity_id,
        "activity_slug": activity_slug,
        "activity_title": activity_title,
        "member_id": member_id,
        "member_readable_id": member_readable_id,
        "role": role,
        "description": description,
        "evidence_links": evidence_links,
        "status": ReportStatus.PENDING.value,
        "version": 0,
        "client_request_id": client_request_id,
        "submitted_at": now,
        "updated_at": now,
        "reviewed_at": None,
        "reviewed_by": None,
        "review_feedback": None,
        "review_history": [],
    }
    result = await _collection().insert_one(doc)
    doc["_id"] = result.inserted_id
    return _to_report(doc)


async def find_by_id(report_id: str) -> ProgressReport | None:
    if not ObjectId.is_valid(report_id):
        return None
    doc = await _collection().find_one({"_id": ObjectId(report_id)})
    return _to_report(doc) if doc else None


async def find_by_client_request(
    member_id: str, client_request_id: str
) -> ProgressReport | None:
    doc = await _collection().find_one(
        {"member_id": member_id, "client_request_id": client_request_id}
    )
    return _to_report(doc) if doc else None


async def update_report(
    report_id: str,
    fields: dict,
    *,
    review_entry: ReportReviewEntry | None = None,
) -> ProgressReport | None:
    """Apply an already-validated set of fields, optionally appending one
    immutable review-history entry (never replacing earlier entries)."""
    update: dict = {
        "$set": {**fields, "updated_at": datetime.now(timezone.utc)}
    }
    if review_entry is not None:
        update["$push"] = {"review_history": review_entry.model_dump()}
    if not ObjectId.is_valid(report_id):
        return None
    doc = await _collection().find_one_and_update(
        {"_id": ObjectId(report_id)}, update, return_document=ReturnDocument.AFTER
    )
    return _to_report(doc) if doc else None


async def list_reports(
    *,
    query: dict,
    sort: list[tuple],
    skip: int,
    limit: int,
) -> tuple[list[ProgressReport], int]:
    collection = _collection()
    total = await collection.count_documents(query)
    cursor = collection.find(query).sort(sort).skip(skip).limit(limit)
    docs = await cursor.to_list(length=limit)
    return [_to_report(doc) for doc in docs], total


async def find_all(query: dict, *, sort: list[tuple], limit: int) -> list[ProgressReport]:
    """Fetch (a bounded number of) matching reports with no pagination offset —
    used for the grouped contribution history."""
    cursor = _collection().find(query).sort(sort).limit(limit)
    return [_to_report(doc) async for doc in cursor]


async def approved_source_rows() -> list[dict]:
    """Return (activity_id, member_id, report_id, version, updated_at) for every
    approved report.

    A single, whole-collection projection used by the AI summarization feature to
    group approved sources and compute source hashes without duplicating the
    reports query shape or reaching into this module's collection.
    """
    cursor = _collection().find(
        {"status": ReportStatus.APPROVED.value},
        {"activity_id": 1, "member_id": 1, "version": 1, "updated_at": 1},
    )
    rows: list[dict] = []
    async for doc in cursor:
        rows.append(
            {
                "activity_id": doc["activity_id"],
                "member_id": doc["member_id"],
                "report_id": str(doc["_id"]),
                "version": int(doc.get("version", 0)),
                "updated_at": doc["updated_at"],
            }
        )
    return rows



async def status_counts_by_activity(member_id: str) -> dict[str, dict]:
    """Return {activity_id: {total, pending, changes_requested, approved,
    last_report_at}} for one member in a single aggregation (avoids N+1)."""
    pipeline = [
        {"$match": {"member_id": member_id}},
        {
            "$group": {
                "_id": "$activity_id",
                "total": {"$sum": 1},
                "pending": {
                    "$sum": {"$cond": [{"$eq": ["$status", ReportStatus.PENDING.value]}, 1, 0]}
                },
                "changes_requested": {
                    "$sum": {
                        "$cond": [
                            {"$eq": ["$status", ReportStatus.CHANGES_REQUESTED.value]},
                            1,
                            0,
                        ]
                    }
                },
                "approved": {
                    "$sum": {"$cond": [{"$eq": ["$status", ReportStatus.APPROVED.value]}, 1, 0]}
                },
                "last_report_at": {"$max": "$submitted_at"},
            }
        },
    ]
    out: dict[str, dict] = {}
    async for row in _collection().aggregate(pipeline):
        out[row["_id"]] = {
            "total": int(row.get("total", 0)),
            "pending": int(row.get("pending", 0)),
            "changes_requested": int(row.get("changes_requested", 0)),
            "approved": int(row.get("approved", 0)),
            "last_report_at": row.get("last_report_at"),
        }
    return out
