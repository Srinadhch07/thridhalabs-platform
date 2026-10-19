"""Data access for the activity-certificate collections.

Three collections, all owned exclusively by this subsystem:

  * `activity_certificates`         — issued credentials.
  * `activity_certificate_audit`    — append-only history.
  * `activity_certificate_templates`— the single editable template document.

Uniqueness is enforced at the database level:

  * `certificate_id` — globally unique public identifier.
  * `(activity_id, member_id, award_key)` — at most one certificate per award
    for a recipient; the atomic guard against duplicate/concurrent issuance.
    Distinct awards (different `award_key`) for the same recipient are allowed.
"""

from __future__ import annotations

from datetime import datetime, timezone

from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorCollection
from pymongo import DESCENDING, ReturnDocument
from pymongo.errors import DuplicateKeyError  # noqa: F401  (re-exported)

from app.core.bson import serialize_for_mongo
from app.db.mongo import get_mongo
from app.models.activity_certificate import (
    ActivityCertificate,
    ActivityCertificateAuditAction,
    ActivityCertificateAuditEntry,
    ActivityCertificateEmailStatus,
    ActivityCertificateStatus,
    ActivityCertificateTemplate,
)

COLLECTION = "activity_certificates"
AUDIT_COLLECTION = "activity_certificate_audit"
TEMPLATE_COLLECTION = "activity_certificate_templates"
TEMPLATE_SINGLETON = "activity_certificate"


def _collection() -> AsyncIOMotorCollection:
    return get_mongo().database[COLLECTION]


def _audit_collection() -> AsyncIOMotorCollection:
    return get_mongo().database[AUDIT_COLLECTION]


def _template_collection() -> AsyncIOMotorCollection:
    return get_mongo().database[TEMPLATE_COLLECTION]


def _to_certificate(doc: dict) -> ActivityCertificate:
    return ActivityCertificate(
        id=str(doc["_id"]),
        certificate_id=doc["certificate_id"],
        activity_id=doc["activity_id"],
        activity_title=doc["activity_title"],
        activity_slug=doc["activity_slug"],
        activity_type=doc["activity_type"],
        award_category=doc["award_category"],
        award_label=doc["award_label"],
        award_statement=doc.get("award_statement", ""),
        award_key=doc["award_key"],
        member_id=doc["member_id"],
        member_readable_id=doc["member_readable_id"],
        member_name=doc["member_name"],
        work_id=doc.get("work_id"),
        work_title=doc.get("work_title"),
        work_slug=doc.get("work_slug"),
        status=ActivityCertificateStatus(
            doc.get("status", ActivityCertificateStatus.ISSUED.value)
        ),
        template_version=doc.get("template_version", "1"),
        template_snapshot=doc.get("template_snapshot", {}),
        issued_at=doc["issued_at"],
        issued_by=doc["issued_by"],
        issued_by_role=doc["issued_by_role"],
        pdf_object_key=doc["pdf_object_key"],
        pdf_filename=doc["pdf_filename"],
        pdf_size_bytes=doc["pdf_size_bytes"],
        pdf_sha256=doc["pdf_sha256"],
        qr_verify_url=doc["qr_verify_url"],
        revoked_at=doc.get("revoked_at"),
        revoked_by=doc.get("revoked_by"),
        revocation_reason=doc.get("revocation_reason"),
        email_status=ActivityCertificateEmailStatus(
            doc.get("email_status", ActivityCertificateEmailStatus.NOT_SENT.value)
        ),
        email_sent_at=doc.get("email_sent_at"),
        email_last_error=doc.get("email_last_error"),
        email_attempts=doc.get("email_attempts", 0),
        created_at=doc["created_at"],
        updated_at=doc["updated_at"],
    )


async def insert_certificate(
    *,
    certificate_id: str,
    activity_id: str,
    activity_title: str,
    activity_slug: str,
    activity_type: str,
    award_category: str,
    award_label: str,
    award_statement: str,
    award_key: str,
    member_id: str,
    member_readable_id: str,
    member_name: str,
    work_id: str | None,
    work_title: str | None,
    work_slug: str | None,
    template_version: str,
    template_snapshot: dict,
    issued_at: datetime,
    issued_by: str,
    issued_by_role: str,
    pdf_object_key: str,
    pdf_filename: str,
    pdf_size_bytes: int,
    pdf_sha256: str,
    qr_verify_url: str,
) -> ActivityCertificate:
    now = datetime.now(timezone.utc)
    doc = {
        "certificate_id": certificate_id,
        "activity_id": activity_id,
        "activity_title": activity_title,
        "activity_slug": activity_slug,
        "activity_type": activity_type,
        "award_category": award_category,
        "award_label": award_label,
        "award_statement": award_statement,
        "award_key": award_key,
        "member_id": member_id,
        "member_readable_id": member_readable_id,
        "member_name": member_name,
        "work_id": work_id,
        "work_title": work_title,
        "work_slug": work_slug,
        "status": ActivityCertificateStatus.ISSUED.value,
        "template_version": template_version,
        "template_snapshot": template_snapshot,
        "issued_at": issued_at,
        "issued_by": issued_by,
        "issued_by_role": issued_by_role,
        "pdf_object_key": pdf_object_key,
        "pdf_filename": pdf_filename,
        "pdf_size_bytes": pdf_size_bytes,
        "pdf_sha256": pdf_sha256,
        "qr_verify_url": qr_verify_url,
        "revoked_at": None,
        "revoked_by": None,
        "revocation_reason": None,
        "email_status": ActivityCertificateEmailStatus.NOT_SENT.value,
        "email_sent_at": None,
        "email_last_error": None,
        "email_attempts": 0,
        "created_at": now,
        "updated_at": now,
    }
    result = await _collection().insert_one(serialize_for_mongo(doc))
    doc["_id"] = result.inserted_id
    return _to_certificate(doc)


async def find_by_id(record_id: str) -> ActivityCertificate | None:
    if not ObjectId.is_valid(record_id):
        return None
    doc = await _collection().find_one({"_id": ObjectId(record_id)})
    return _to_certificate(doc) if doc else None


async def find_by_public_id(certificate_id: str) -> ActivityCertificate | None:
    doc = await _collection().find_one({"certificate_id": certificate_id})
    return _to_certificate(doc) if doc else None


async def find_by_award(
    activity_id: str, member_id: str, award_key: str
) -> ActivityCertificate | None:
    doc = await _collection().find_one(
        {"activity_id": activity_id, "member_id": member_id, "award_key": award_key}
    )
    return _to_certificate(doc) if doc else None


async def list_issued_keys(activity_id: str, member_ids: list[str]) -> set[tuple[str, str]]:
    """Return {(member_id, award_key)} already issued for an activity."""
    if not member_ids:
        return set()
    cursor = _collection().find(
        {"activity_id": activity_id, "member_id": {"$in": member_ids}},
        {"member_id": 1, "award_key": 1},
    )
    return {(doc["member_id"], doc["award_key"]) async for doc in cursor}


async def update_certificate(
    certificate_id: str, fields: dict
) -> ActivityCertificate | None:
    doc = await _collection().find_one_and_update(
        {"certificate_id": certificate_id},
        {"$set": {**serialize_for_mongo(fields), "updated_at": datetime.now(timezone.utc)}},
        return_document=ReturnDocument.AFTER,
    )
    return _to_certificate(doc) if doc else None


async def list_certificates(
    *, query: dict, skip: int, limit: int
) -> tuple[list[ActivityCertificate], int]:
    collection = _collection()
    total = await collection.count_documents(query)
    cursor = collection.find(query).sort([("issued_at", DESCENDING)]).skip(skip).limit(limit)
    docs = await cursor.to_list(length=limit)
    return [_to_certificate(doc) for doc in docs], total


# ---------------------------------------------------------------------------
# Audit (append-only)
# ---------------------------------------------------------------------------
async def append_audit(
    *,
    certificate_id: str,
    action: ActivityCertificateAuditAction,
    actor_id: str,
    actor_role: str,
    detail: str | None = None,
) -> None:
    now = datetime.now(timezone.utc)
    await _audit_collection().insert_one(
        {
            "certificate_id": certificate_id,
            "action": action.value,
            "actor_id": actor_id,
            "actor_role": actor_role,
            "detail": detail,
            "created_at": now,
        }
    )


async def list_audit(certificate_id: str) -> list[ActivityCertificateAuditEntry]:
    cursor = _audit_collection().find({"certificate_id": certificate_id}).sort(
        [("created_at", DESCENDING)]
    )
    out: list[ActivityCertificateAuditEntry] = []
    async for doc in cursor:
        out.append(
            ActivityCertificateAuditEntry(
                id=str(doc["_id"]),
                certificate_id=doc["certificate_id"],
                action=ActivityCertificateAuditAction(doc["action"]),
                actor_id=doc["actor_id"],
                actor_role=doc["actor_role"],
                detail=doc.get("detail"),
                created_at=doc["created_at"],
            )
        )
    return out


# ---------------------------------------------------------------------------
# Template (singleton)
# ---------------------------------------------------------------------------
def _to_template(doc: dict) -> ActivityCertificateTemplate:
    data = {k: v for k, v in doc.items() if k not in ("_id", "singleton")}
    return ActivityCertificateTemplate(**data)


async def get_template() -> ActivityCertificateTemplate | None:
    doc = await _template_collection().find_one({"singleton": TEMPLATE_SINGLETON})
    return _to_template(doc) if doc else None


async def save_template(
    template: ActivityCertificateTemplate, *, updated_by: str
) -> ActivityCertificateTemplate:
    now = datetime.now(timezone.utc)
    payload = template.model_dump()
    payload["updated_by"] = updated_by
    payload["updated_at"] = now
    payload["singleton"] = TEMPLATE_SINGLETON
    await _template_collection().update_one(
        {"singleton": TEMPLATE_SINGLETON},
        {"$set": serialize_for_mongo(payload)},
        upsert=True,
    )
    doc = await _template_collection().find_one({"singleton": TEMPLATE_SINGLETON})
    assert doc is not None
    return _to_template(doc)
