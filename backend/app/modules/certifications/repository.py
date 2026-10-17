"""Data access for the `certification_requests` collection (no business rules)."""

from __future__ import annotations

from datetime import datetime, timezone

from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorCollection
from pymongo import DESCENDING, ReturnDocument
from pymongo.errors import DuplicateKeyError  # noqa: F401  (re-exported)

from app.db.mongo import get_mongo
from app.models.certification import (
    CertificationDecision,
    CertificationRequest,
    CertificationSnapshot,
    CertificationStatus,
)

COLLECTION = "certification_requests"


def _collection() -> AsyncIOMotorCollection:
    return get_mongo().database[COLLECTION]


def _to_request(doc: dict) -> CertificationRequest:
    return CertificationRequest(
        id=str(doc["_id"]),
        work_id=doc["work_id"],
        member_id=doc["member_id"],
        status=CertificationStatus(doc["status"]),
        active=doc["active"],
        snapshot_version=doc["snapshot_version"],
        version_reviewed=doc["version_reviewed"],
        snapshot=CertificationSnapshot(**doc["snapshot"]),
        captured_at=doc["captured_at"],
        submitted_at=doc["submitted_at"],
        decided_at=doc.get("decided_at"),
        decided_by=doc.get("decided_by"),
        decided_by_role=doc.get("decided_by_role"),
        latest_feedback=doc.get("latest_feedback"),
        decisions=[CertificationDecision(**entry) for entry in doc.get("decisions") or []],
        created_at=doc["created_at"],
        updated_at=doc["updated_at"],
    )


async def find_by_id(request_id: str) -> CertificationRequest | None:
    if not ObjectId.is_valid(request_id):
        return None
    doc = await _collection().find_one({"_id": ObjectId(request_id)})
    return _to_request(doc) if doc else None


async def find_latest_for_work(work_id: str) -> CertificationRequest | None:
    doc = await _collection().find_one(
        {"work_id": work_id}, sort=[("submitted_at", DESCENDING)]
    )
    return _to_request(doc) if doc else None


async def find_latest_by_work_ids(
    work_ids: list[str],
) -> dict[str, CertificationRequest]:
    """Return the most recently submitted request per work id."""
    if not work_ids:
        return {}
    results: dict[str, CertificationRequest] = {}
    cursor = _collection().find(
        {"work_id": {"$in": work_ids}}, sort=[("submitted_at", DESCENDING)]
    )
    async for doc in cursor:
        request = _to_request(doc)
        results.setdefault(request.work_id, request)
    return results


async def find_active_for_work(work_id: str) -> CertificationRequest | None:
    doc = await _collection().find_one({"work_id": work_id, "active": True})
    return _to_request(doc) if doc else None


async def insert_request(
    *,
    work_id: str,
    member_id: str,
    snapshot: CertificationSnapshot,
    snapshot_version: int,
    submitted_at: datetime,
) -> CertificationRequest:
    now = datetime.now(timezone.utc)
    doc = {
        "work_id": work_id,
        "member_id": member_id,
        "status": CertificationStatus.SUBMITTED.value,
        "active": True,
        "snapshot_version": snapshot_version,
        "version_reviewed": snapshot_version,
        "snapshot": snapshot.model_dump(),
        "captured_at": submitted_at,
        "submitted_at": submitted_at,
        "decided_at": None,
        "decided_by": None,
        "decided_by_role": None,
        "latest_feedback": None,
        "decisions": [],
        "created_at": now,
        "updated_at": now,
    }
    result = await _collection().insert_one(doc)
    doc["_id"] = result.inserted_id
    return _to_request(doc)


async def update_request(
    request_id: str,
    fields: dict,
    *,
    decision: CertificationDecision | None = None,
) -> CertificationRequest | None:
    update: dict = {
        "$set": {**fields, "updated_at": datetime.now(timezone.utc)},
    }
    if decision is not None:
        update["$push"] = {"decisions": decision.model_dump()}
    doc = await _collection().find_one_and_update(
        {"_id": ObjectId(request_id)}, update, return_document=ReturnDocument.AFTER
    )
    return _to_request(doc) if doc else None


async def list_requests(
    *,
    query: dict,
    sort: list[tuple],
    skip: int,
    limit: int,
) -> tuple[list[CertificationRequest], int]:
    collection = _collection()
    total = await collection.count_documents(query)
    cursor = collection.find(query).sort(sort).skip(skip).limit(limit)
    docs = await cursor.to_list(length=limit)
    return [_to_request(doc) for doc in docs], total


async def count_by_status(work_id: str, status: CertificationStatus) -> int:
    return await _collection().count_documents(
        {"work_id": work_id, "status": status.value}
    )
