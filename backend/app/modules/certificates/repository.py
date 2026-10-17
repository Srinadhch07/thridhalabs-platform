"""Data access for the `certificates` collection (no business rules here).

Uniqueness is enforced at the database level:

  * `certificate_id` — the public identifier is globally unique.
  * `request_id`     — at most one certificate per certification request; this
    is the atomic guard that makes duplicate/concurrent issuance safe (a
    duplicate-key error is raised even under races).
"""

from __future__ import annotations

from datetime import datetime, timezone

from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorCollection
from pymongo import DESCENDING, ReturnDocument
from pymongo.errors import DuplicateKeyError  # noqa: F401  (re-exported)

from app.core.bson import serialize_for_mongo
from app.db.mongo import get_mongo
from app.models.certificate import (
    Certificate,
    CertificateEmailStatus,
    CertificateStatus,
)

COLLECTION = "certificates"


def _collection() -> AsyncIOMotorCollection:
    return get_mongo().database[COLLECTION]


def _to_certificate(doc: dict) -> Certificate:
    return Certificate(
        id=str(doc["_id"]),
        certificate_id=doc["certificate_id"],
        request_id=doc["request_id"],
        work_id=doc["work_id"],
        member_id=doc["member_id"],
        member_readable_id=doc["member_readable_id"],
        member_name=doc["member_name"],
        work_title=doc["work_title"],
        work_slug=doc["work_slug"],
        status=CertificateStatus(doc.get("status", CertificateStatus.ISSUED.value)),
        template_version=doc.get("template_version", "1"),
        decided_at=doc.get("decided_at"),
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
        email_status=CertificateEmailStatus(
            doc.get("email_status", CertificateEmailStatus.NOT_SENT.value)
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
    request_id: str,
    work_id: str,
    member_id: str,
    member_readable_id: str,
    member_name: str,
    work_title: str,
    work_slug: str,
    decided_at: datetime | None,
    issued_at: datetime,
    issued_by: str,
    issued_by_role: str,
    template_version: str,
    pdf_object_key: str,
    pdf_filename: str,
    pdf_size_bytes: int,
    pdf_sha256: str,
    qr_verify_url: str,
) -> Certificate:
    now = datetime.now(timezone.utc)
    doc = {
        "certificate_id": certificate_id,
        "request_id": request_id,
        "work_id": work_id,
        "member_id": member_id,
        "member_readable_id": member_readable_id,
        "member_name": member_name,
        "work_title": work_title,
        "work_slug": work_slug,
        "status": CertificateStatus.ISSUED.value,
        "template_version": template_version,
        "decided_at": decided_at,
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
        "email_status": CertificateEmailStatus.NOT_SENT.value,
        "email_sent_at": None,
        "email_last_error": None,
        "email_attempts": 0,
        "created_at": now,
        "updated_at": now,
    }
    result = await _collection().insert_one(serialize_for_mongo(doc))
    doc["_id"] = result.inserted_id
    return _to_certificate(doc)


async def find_by_id(record_id: str) -> Certificate | None:
    if not ObjectId.is_valid(record_id):
        return None
    doc = await _collection().find_one({"_id": ObjectId(record_id)})
    return _to_certificate(doc) if doc else None


async def find_by_public_id(certificate_id: str) -> Certificate | None:
    doc = await _collection().find_one({"certificate_id": certificate_id})
    return _to_certificate(doc) if doc else None


async def find_by_request_id(request_id: str) -> Certificate | None:
    doc = await _collection().find_one({"request_id": request_id})
    return _to_certificate(doc) if doc else None


async def update_certificate(
    certificate_id: str, fields: dict
) -> Certificate | None:
    doc = await _collection().find_one_and_update(
        {"certificate_id": certificate_id},
        {"$set": {**serialize_for_mongo(fields), "updated_at": datetime.now(timezone.utc)}},
        return_document=ReturnDocument.AFTER,
    )
    return _to_certificate(doc) if doc else None


async def list_certificates(
    *,
    query: dict,
    skip: int,
    limit: int,
) -> tuple[list[Certificate], int]:
    collection = _collection()
    total = await collection.count_documents(query)
    cursor = collection.find(query).sort([("issued_at", DESCENDING)]).skip(skip).limit(limit)
    docs = await cursor.to_list(length=limit)
    return [_to_certificate(doc) for doc in docs], total
