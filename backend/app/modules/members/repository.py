"""Data access for the `members` collection (no business rules here).

Member records are addressed internally by their MongoDB `_id`; the readable
`member_id` (THL-M-YYYY-NNNN) is a separate, unique, permanent identifier.
"""

from __future__ import annotations

from datetime import datetime, timezone

from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorCollection
from pymongo import ReturnDocument
from pymongo.errors import DuplicateKeyError  # noqa: F401  (re-exported for callers)

from app.db.mongo import get_mongo
from app.models.member import (
    Member,
    MemberOnboarding,
    MemberProfile,
    MemberStatus,
)

COLLECTION = "members"
COUNTER_COLLECTION = "members_counters"


def _collection() -> AsyncIOMotorCollection:
    return get_mongo().database[COLLECTION]


def _counters() -> AsyncIOMotorCollection:
    return get_mongo().database[COUNTER_COLLECTION]


def _to_member(doc: dict) -> Member:
    return Member(
        id=str(doc["_id"]),
        member_id=doc["member_id"],
        email=doc["email"],
        password_hash=doc.get("password_hash"),
        status=MemberStatus(doc.get("status", MemberStatus.PENDING_SETUP.value)),
        token_version=doc.get("token_version", 0),
        full_name=doc.get("full_name"),
        role_label=doc.get("role_label"),
        joined_opportunity_id=doc.get("joined_opportunity_id"),
        internal_note=doc.get("internal_note"),
        created_by=doc["created_by"],
        created_at=doc["created_at"],
        updated_at=doc["updated_at"],
        last_login_at=doc.get("last_login_at"),
        onboarding=MemberOnboarding(**(doc.get("onboarding") or {})),
        profile=MemberProfile(**(doc.get("profile") or {})),
    )


async def allocate_member_id() -> str:
    """Atomically allocate the next readable member id for the current year.

    Uses a dedicated per-year counter document with `$inc` — never a document
    count. Sequential ids are never reused, even after deletion.
    """
    year = datetime.now(timezone.utc).year
    counter = await _counters().find_one_and_update(
        {"_id": f"member_id:{year}"},
        {"$inc": {"seq": 1}},
        upsert=True,
        return_document=ReturnDocument.AFTER,
    )
    seq = int(counter["seq"])
    return f"THL-M-{year}-{seq:04d}"


async def find_by_id(record_id: str) -> Member | None:
    if not ObjectId.is_valid(record_id):
        return None
    doc = await _collection().find_one({"_id": ObjectId(record_id)})
    return _to_member(doc) if doc else None


async def find_by_email(email: str) -> Member | None:
    doc = await _collection().find_one({"email": email})
    return _to_member(doc) if doc else None


async def find_by_readable_id(member_id: str) -> Member | None:
    """Look a member up by their permanent readable id (THL-M-YYYY-NNNN)."""
    doc = await _collection().find_one({"member_id": member_id})
    return _to_member(doc) if doc else None


async def find_many_by_ids(ids: list[str]) -> dict[str, Member]:
    """Fetch several members by internal id in one query (avoids N+1)."""
    valid = [ObjectId(i) for i in ids if ObjectId.is_valid(i)]
    if not valid:
        return {}
    found: dict[str, Member] = {}
    async for doc in _collection().find({"_id": {"$in": valid}}):
        member = _to_member(doc)
        found[member.id] = member
    return found


async def search_member_ids(pattern: str, *, limit: int = 500) -> list[str]:
    """Return internal ids of members whose name, email or readable id matches
    a (already-escaped) case-insensitive regex `pattern`."""
    query = {
        "$or": [
            {"full_name": {"$regex": pattern, "$options": "i"}},
            {"email": {"$regex": pattern, "$options": "i"}},
            {"member_id": {"$regex": pattern, "$options": "i"}},
        ]
    }
    cursor = _collection().find(query, {"_id": 1}).limit(limit)
    return [str(doc["_id"]) async for doc in cursor]


async def find_by_onboarding_token_hash(token_hash: str) -> Member | None:
    doc = await _collection().find_one({"onboarding.token_hash": token_hash})
    return _to_member(doc) if doc else None


async def email_exists(email: str, *, exclude_id: str | None = None) -> bool:
    query: dict = {"email": email}
    if exclude_id and ObjectId.is_valid(exclude_id):
        query["_id"] = {"$ne": ObjectId(exclude_id)}
    return await _collection().find_one(query, {"_id": 1}) is not None


async def insert_member(
    *,
    member_id: str,
    email: str,
    full_name: str | None,
    role_label: str | None,
    joined_opportunity_id: str | None,
    internal_note: str | None,
    created_by: str,
    onboarding: MemberOnboarding,
) -> Member:
    """Insert a new member. Raises `DuplicateKeyError` on a duplicate email or
    member id (the unique indexes enforce both under races)."""
    now = datetime.now(timezone.utc)
    doc = {
        "member_id": member_id,
        "email": email,
        "password_hash": None,
        "status": MemberStatus.PENDING_SETUP.value,
        "token_version": 0,
        "full_name": full_name,
        "role_label": role_label,
        "joined_opportunity_id": joined_opportunity_id,
        "internal_note": internal_note,
        "created_by": created_by,
        "created_at": now,
        "updated_at": now,
        "last_login_at": None,
        "onboarding": onboarding.model_dump(),
        "profile": MemberProfile().model_dump(),
    }
    result = await _collection().insert_one(doc)
    doc["_id"] = result.inserted_id
    return _to_member(doc)


async def update_admin_fields(record_id: str, fields: dict) -> Member | None:
    """Apply an already-validated set of admin-managed fields."""
    update = {**fields, "updated_at": datetime.now(timezone.utc)}
    doc = await _collection().find_one_and_update(
        {"_id": ObjectId(record_id)},
        {"$set": update},
        return_document=ReturnDocument.AFTER,
    )
    return _to_member(doc) if doc else None


async def set_onboarding(record_id: str, onboarding: MemberOnboarding) -> Member | None:
    doc = await _collection().find_one_and_update(
        {"_id": ObjectId(record_id)},
        {
            "$set": {
                "onboarding": onboarding.model_dump(),
                "updated_at": datetime.now(timezone.utc),
            }
        },
        return_document=ReturnDocument.AFTER,
    )
    return _to_member(doc) if doc else None


async def set_password_and_complete_onboarding(
    record_id: str,
    *,
    password_hash: str,
    completed_at: datetime,
    status: MemberStatus,
) -> Member | None:
    doc = await _collection().find_one_and_update(
        {"_id": ObjectId(record_id)},
        {
            "$set": {
                "password_hash": password_hash,
                "status": status.value,
                "onboarding.token_hash": None,
                "onboarding.completed_at": completed_at,
                "updated_at": datetime.now(timezone.utc),
            }
        },
        return_document=ReturnDocument.AFTER,
    )
    return _to_member(doc) if doc else None


async def set_password_hash(record_id: str, password_hash: str) -> Member | None:
    doc = await _collection().find_one_and_update(
        {"_id": ObjectId(record_id)},
        {
            "$set": {
                "password_hash": password_hash,
                "updated_at": datetime.now(timezone.utc),
            }
        },
        return_document=ReturnDocument.AFTER,
    )
    return _to_member(doc) if doc else None


async def set_profile(
    record_id: str,
    *,
    profile: MemberProfile,
    status: MemberStatus,
) -> Member | None:
    doc = await _collection().find_one_and_update(
        {"_id": ObjectId(record_id)},
        {
            "$set": {
                "profile": profile.model_dump(),
                "status": status.value,
                "updated_at": datetime.now(timezone.utc),
            }
        },
        return_document=ReturnDocument.AFTER,
    )
    return _to_member(doc) if doc else None


async def set_status(record_id: str, status: MemberStatus) -> Member | None:
    doc = await _collection().find_one_and_update(
        {"_id": ObjectId(record_id)},
        {
            "$set": {
                "status": status.value,
                "updated_at": datetime.now(timezone.utc),
            }
        },
        return_document=ReturnDocument.AFTER,
    )
    return _to_member(doc) if doc else None


async def bump_token_version(record_id: str) -> int:
    """Increment token_version (revokes every outstanding member token)."""
    doc = await _collection().find_one_and_update(
        {"_id": ObjectId(record_id)},
        {
            "$inc": {"token_version": 1},
            "$set": {"updated_at": datetime.now(timezone.utc)},
        },
        return_document=ReturnDocument.AFTER,
    )
    if doc is None:
        raise LookupError("member not found")
    return int(doc["token_version"])


async def touch_last_login(record_id: str) -> None:
    await _collection().update_one(
        {"_id": ObjectId(record_id)},
        {
            "$set": {
                "last_login_at": datetime.now(timezone.utc),
                "updated_at": datetime.now(timezone.utc),
            }
        },
    )


async def list_members(
    *,
    page: int,
    page_size: int,
    query: dict,
    sort: list[tuple],
) -> tuple[list[Member], int]:
    collection = _collection()
    total = await collection.count_documents(query)
    cursor = (
        collection.find(query)
        .sort(sort)
        .skip((page - 1) * page_size)
        .limit(page_size)
    )
    docs = await cursor.to_list(length=page_size)
    return [_to_member(doc) for doc in docs], total


async def delete_by_id(record_id: str) -> bool:
    result = await _collection().delete_one({"_id": ObjectId(record_id)})
    return result.deleted_count == 1