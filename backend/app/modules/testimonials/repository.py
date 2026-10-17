"""Data access for the `testimonials` collection (no business rules here)."""

from __future__ import annotations

from datetime import datetime, timezone

from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorCollection

from app.db.mongo import get_mongo
from app.models.testimonial import Testimonial, TestimonialStatus

COLLECTION = "testimonials"


def _resolve_status(doc: dict) -> TestimonialStatus:
    """Read moderation status with a safe fallback for pre-moderation docs.

    Documents written before the moderation workflow carry no `status`;
    those that were publicly visible (`published`) read as approved so
    existing public content never disappears, everything else as pending.
    """
    raw = doc.get("status")
    if raw is None:
        return (
            TestimonialStatus.APPROVED
            if doc.get("published")
            else TestimonialStatus.PENDING
        )
    return TestimonialStatus(raw)


def _collection() -> AsyncIOMotorCollection:
    return get_mongo().database[COLLECTION]


def _to_testimonial(doc: dict) -> Testimonial:
    return Testimonial(
        id=str(doc["_id"]),
        client_id=doc.get("client_id"),
        person_name=doc["person_name"],
        role=doc.get("role", ""),
        testimonial_text=doc["testimonial_text"],
        profile_image_media_id=doc.get("profile_image_media_id"),
        company=doc.get("company"),
        rating=doc.get("rating", 5),
        featured=doc.get("featured", False),
        published=doc.get("published", False),
        status=_resolve_status(doc),
        display_order=doc.get("display_order", 0),
        date=doc.get("date"),
        created_at=doc["created_at"],
        updated_at=doc["updated_at"],
    )


async def insert(*, person_name: str, testimonial_text: str, **fields) -> Testimonial:
    now = datetime.now(timezone.utc)
    doc = {
        "client_id": fields.get("client_id"),
        "person_name": person_name,
        "role": fields.get("role", ""),
        "testimonial_text": testimonial_text,
        "profile_image_media_id": fields.get("profile_image_media_id"),
        "company": fields.get("company"),
        "rating": fields.get("rating", 5),
        "featured": fields.get("featured", False),
        "published": fields.get("published", False),
        "status": fields.get("status", TestimonialStatus.PENDING.value),
        "display_order": fields.get("display_order", 0),
        "date": fields.get("date"),
        "created_at": now,
        "updated_at": now,
    }
    result = await _collection().insert_one(doc)
    doc["_id"] = result.inserted_id
    return _to_testimonial(doc)


async def find_by_id(testimonial_id: str) -> Testimonial | None:
    if not ObjectId.is_valid(testimonial_id):
        return None
    doc = await _collection().find_one({"_id": ObjectId(testimonial_id)})
    return _to_testimonial(doc) if doc else None


async def update(testimonial_id: str, fields: dict, *, now: datetime | None = None) -> Testimonial | None:
    if not ObjectId.is_valid(testimonial_id):
        return None
    update = dict(fields)
    update["updated_at"] = now or datetime.now(timezone.utc)
    result = await _collection().update_one(
        {"_id": ObjectId(testimonial_id)}, {"$set": update}
    )
    if result.matched_count == 0:
        return None
    return await find_by_id(testimonial_id)


async def delete_by_id(testimonial_id: str) -> bool:
    if not ObjectId.is_valid(testimonial_id):
        return False
    result = await _collection().delete_one({"_id": ObjectId(testimonial_id)})
    return result.deleted_count > 0


async def list_testimonials(
    *, query: dict, sort: list[tuple], skip: int, limit: int
) -> tuple[list[Testimonial], int]:
    cursor = _collection().find(query).sort(sort).skip(skip).limit(limit)
    items = [_to_testimonial(doc) async for doc in cursor]
    total = await _collection().count_documents(query)
    return items, total


async def count_by_client(client_id: str) -> int:
    return await _collection().count_documents({"client_id": client_id})