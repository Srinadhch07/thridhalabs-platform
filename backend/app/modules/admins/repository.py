"""Data access for the `admins` collection (no business rules here)."""

from __future__ import annotations

from datetime import datetime, timezone

from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorCollection
from pymongo import ReturnDocument
from pymongo.errors import DuplicateKeyError  # noqa: F401  (re-exported for callers)

from app.db.mongo import get_mongo
from app.models.admin import Admin

COLLECTION = "admins"


def _collection() -> AsyncIOMotorCollection:
    return get_mongo().database[COLLECTION]


def _to_admin(doc: dict) -> Admin:
    return Admin(
        id=str(doc["_id"]),
        email=doc["email"],
        password_hash=doc["password_hash"],
        role=doc["role"],
        is_active=doc.get("is_active", True),
        token_version=doc.get("token_version", 0),
        created_at=doc["created_at"],
        updated_at=doc["updated_at"],
        last_login_at=doc.get("last_login_at"),
    )


async def find_by_email(email: str) -> Admin | None:
    doc = await _collection().find_one({"email": email})
    return _to_admin(doc) if doc else None


async def find_by_id(admin_id: str) -> Admin | None:
    if not ObjectId.is_valid(admin_id):
        return None
    doc = await _collection().find_one({"_id": ObjectId(admin_id)})
    return _to_admin(doc) if doc else None


async def insert_admin(
    *, email: str, password_hash: str, role: str, is_active: bool
) -> Admin:
    """Insert a new admin. Raises `DuplicateKeyError` on an existing email."""
    now = datetime.now(timezone.utc)
    doc = {
        "email": email,
        "password_hash": password_hash,
        "role": role,
        "is_active": is_active,
        "token_version": 0,
        "created_at": now,
        "updated_at": now,
        "last_login_at": None,
    }
    result = await _collection().insert_one(doc)
    doc["_id"] = result.inserted_id
    return _to_admin(doc)


async def touch_last_login(admin_id: str) -> None:
    await _collection().update_one(
        {"_id": ObjectId(admin_id)},
        {"$set": {"last_login_at": datetime.now(timezone.utc),
                  "updated_at": datetime.now(timezone.utc)}},
    )


async def bump_token_version(admin_id: str) -> int:
    """Increment token_version (revokes every outstanding token) and return it."""
    doc = await _collection().find_one_and_update(
        {"_id": ObjectId(admin_id)},
        {"$inc": {"token_version": 1},
         "$set": {"updated_at": datetime.now(timezone.utc)}},
        return_document=ReturnDocument.AFTER,
    )
    if doc is None:
        raise LookupError("admin not found")
    return int(doc["token_version"])


async def email_exists(email: str) -> bool:
    return await _collection().find_one({"email": email}, {"_id": 1}) is not None
