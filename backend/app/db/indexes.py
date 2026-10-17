"""Startup index initialization (no manual database setup required)."""

from __future__ import annotations

import pymongo

from app.core.logging import get_logger
from app.db.mongo import get_mongo

log = get_logger("db.indexes")

_indexes_ready = False


async def ensure_indexes(force: bool = False) -> None:
    """Create/verify the indexes the application depends on.

    - `admins.email` unique — enforces account uniqueness at the database
      level (a duplicate key error is raised even under races).
    - `media.checksum + media.storage_mode` unique — de-duplication of
      identical uploaded content per storage mode.
    - `media.created_at` (descending) — newest-first listing.
    - `media.media_type` — media-type filtering.
    Runs once per process; called from the application lifespan only when
    MongoDB is reachable.
    """
    global _indexes_ready
    if _indexes_ready and not force:
        return

    db = get_mongo().database
    await db.admins.create_index("email", unique=True)
    await db.media.create_index(
        [("checksum", pymongo.ASCENDING), ("storage_mode", pymongo.ASCENDING)],
        unique=True,
    )
    await db.media.create_index([("created_at", pymongo.DESCENDING)])
    await db.media.create_index([("media_type", pymongo.ASCENDING)])

    # Phase 4 — content collections.
    await db.settings.create_index("singleton", unique=True)
    await db.branding.create_index("singleton", unique=True)

    await db.clients.create_index("slug", unique=True)
    await db.clients.create_index(
        [("display_order", pymongo.ASCENDING), ("created_at", pymongo.DESCENDING)]
    )
    await db.clients.create_index("featured")
    await db.clients.create_index("category")

    await db.projects.create_index("slug", unique=True)
    await db.projects.create_index("client_id")
    await db.projects.create_index("status")
    await db.projects.create_index("project_type")
    await db.projects.create_index("featured")
    await db.projects.create_index("display_order")
    await db.projects.create_index("category")

    await db.testimonials.create_index("client_id")
    await db.testimonials.create_index("published")
    await db.testimonials.create_index("featured")
    await db.testimonials.create_index("display_order")

    # Phase 8 — careers.
    await db.careers_settings.create_index("singleton", unique=True)
    await db.careers_opportunities.create_index("slug", unique=True)
    await db.careers_opportunities.create_index("type")
    await db.careers_opportunities.create_index(
        [
            ("status", pymongo.ASCENDING),
            ("display_order", pymongo.ASCENDING),
            ("created_at", pymongo.DESCENDING),
        ]
    )

    # Member accounts.
    # - email + member_id are permanent unique identifiers (also enforced by
    #   the atomic per-year counter, but the unique indexes win any race).
    # - onboarding token hashes are unique and only indexed while they hold a
    #   real hash (a partial index, because completed/cleared tokens store
    #   `null` and many members legitimately have no live token).
    await db.members.create_index("email", unique=True)
    await db.members.create_index("member_id", unique=True)
    await db.members.create_index(
        "onboarding.token_hash",
        unique=True,
        partialFilterExpression={"onboarding.token_hash": {"$type": "string"}},
    )
    await db.members.create_index("onboarding.expires_at")
    await db.members.create_index(
        [
            ("status", pymongo.ASCENDING),
            ("created_at", pymongo.DESCENDING),
        ]
    )
    await db.members.create_index("full_name")
    # Per-year sequential member-id counters (atomic $inc source of truth).
    # The `_id` itself (`member_id:{year}`) is the unique key; no extra index.

    # Work showcase + certification review.
    # - works: slug is unique *per member* (the same title may repeat across
    #   different members); shared listing/status/visibility queries.
    await db.member_works.create_index(
        [("member_id", pymongo.ASCENDING), ("slug", pymongo.ASCENDING)],
        unique=True,
    )
    await db.member_works.create_index(
        [("member_id", pymongo.ASCENDING), ("created_at", pymongo.DESCENDING)]
    )
    await db.member_works.create_index(
        [
            ("publication_status", pymongo.ASCENDING),
            ("visibility", pymongo.ASCENDING),
        ]
    )
    # Publication-review queue (admin) and official featuring.
    await db.member_works.create_index(
        [
            ("publication_status", pymongo.ASCENDING),
            ("submitted_at", pymongo.DESCENDING),
        ]
    )
    await db.member_works.create_index(
        [
            ("featured_on_projects", pymongo.ASCENDING),
            ("publication_status", pymongo.ASCENDING),
        ]
    )
    # - certification_requests: at most one ACTIVE request per work. Mongo does
    #   not support `$nin` in a partialFilterExpression, so an explicit boolean
    #   `active` field is used (false once a request is approved/rejected).
    await db.certification_requests.create_index(
        "work_id",
        unique=True,
        partialFilterExpression={"active": True},
    )
    await db.certification_requests.create_index(
        [("member_id", pymongo.ASCENDING), ("submitted_at", pymongo.DESCENDING)]
    )
    await db.certification_requests.create_index(
        [("status", pymongo.ASCENDING), ("submitted_at", pymongo.DESCENDING)]
    )

    # Issued certificates.
    # - certificate_id: the public, collision-resistant identifier — globally
    #   unique so a random id is never issued twice (retried on duplicate-key).
    # - request_id: at most ONE certificate per certification request; this is
    #   the atomic guard that makes duplicate/concurrent issuance safe.
    await db.certificates.create_index("certificate_id", unique=True)
    await db.certificates.create_index("request_id", unique=True)
    await db.certificates.create_index(
        [("issued_at", pymongo.DESCENDING)]
    )
    await db.certificates.create_index(
        [("member_id", pymongo.ASCENDING), ("issued_at", pymongo.DESCENDING)]
    )
    await db.certificates.create_index("status")

    # Activities (Phase 1) — project/programme/hackathon management.
    # - slug is unique (public detail pages are slug-addressed).
    # - listing/lifecycle filters mirror the admin + public query shapes.
    await db.activities.create_index("slug", unique=True)
    await db.activities.create_index("status")
    await db.activities.create_index("activity_type")
    await db.activities.create_index("featured")
    await db.activities.create_index("display_order")
    await db.activities.create_index(
        [
            ("status", pymongo.ASCENDING),
            ("display_order", pymongo.ASCENDING),
            ("created_at", pymongo.DESCENDING),
        ]
    )
    # Participations — one record per (activity, member) is the atomic guard
    # that makes open self-registration duplicate-safe.
    await db.activity_participations.create_index(
        [("activity_id", pymongo.ASCENDING), ("member_id", pymongo.ASCENDING)],
        unique=True,
    )
    await db.activity_participations.create_index(
        [("activity_id", pymongo.ASCENDING), ("status", pymongo.ASCENDING)]
    )
    await db.activity_participations.create_index(
        [("member_id", pymongo.ASCENDING), ("created_at", pymongo.DESCENDING)]
    )

    # Project progress reports.
    # - client_request_id is the idempotency guard: at most one report per
    #   (member, client-supplied request id), so a retried submission returns
    #   the original instead of creating a duplicate.
    # - listing/queue/history query shapes are mirrored below.
    await db.progress_reports.create_index(
        [("member_id", pymongo.ASCENDING), ("client_request_id", pymongo.ASCENDING)],
        unique=True,
        partialFilterExpression={"client_request_id": {"$type": "string"}},
    )
    await db.progress_reports.create_index(
        [("member_id", pymongo.ASCENDING), ("submitted_at", pymongo.DESCENDING)]
    )
    await db.progress_reports.create_index(
        [("status", pymongo.ASCENDING), ("submitted_at", pymongo.DESCENDING)]
    )
    await db.progress_reports.create_index(
        [("activity_id", pymongo.ASCENDING), ("status", pymongo.ASCENDING)]
    )
    await db.progress_reports.create_index(
        [
            ("activity_id", pymongo.ASCENDING),
            ("member_id", pymongo.ASCENDING),
            ("status", pymongo.ASCENDING),
        ]
    )

    # AI work summaries (Groq).
    # - ai_settings: the single AI settings document.
    # - ai_summaries: at most ONE summary per (project, member); plus the
    #   published-listing query shape used by the member contribution history.
    await db.ai_settings.create_index("singleton", unique=True)
    await db.ai_summaries.create_index(
        [("activity_id", pymongo.ASCENDING), ("member_id", pymongo.ASCENDING)],
        unique=True,
    )
    await db.ai_summaries.create_index(
        [("member_id", pymongo.ASCENDING), ("status", pymongo.ASCENDING)]
    )
    await db.ai_summaries.create_index(
        [("status", pymongo.ASCENDING), ("updated_at", pymongo.DESCENDING)]
    )

    _indexes_ready = True
    log.info(
        "Database indexes ensured (admins, media, settings, branding, clients, "
        "projects, testimonials, careers, members, works, certifications, "
        "certificates, activities, progress reports, ai summaries)"
    )
