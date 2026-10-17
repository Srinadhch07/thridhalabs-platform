"""Certification-review business logic.

Rules enforced here:
  * A member may request a review only for one of their own **published** works.
  * One *active* request per work — re-applying while one is live is rejected;
    a `changes_requested` request is resubmitted in place (same request, fresh
    snapshot) instead of spawning a second review.
  * The work is snapshotted (frozen) at submission; reviewers only ever see the
    snapshot. `changed_since_review` is derived later from the work's version.
  * Approving/rejecting deactivates the request (freeing the unique slot);
    requesting changes keeps it active.
  * Only admins/owners (`require_role("admin")`) may decide.
"""

from __future__ import annotations

from datetime import datetime, timezone

from pymongo.errors import DuplicateKeyError

from app.core.errors import AppError
from app.core.logging import get_logger
from app.models.admin import Admin
from app.models.certificate import CertificateRef
from app.models.certification import (
    CertificationDecision,
    CertificationRequest,
    CertificationSnapshot,
    CertificationStatus,
    TERMINAL_STATUSES,
)
from app.models.member import Member
from app.models.work import MemberWork, WorkPublicationStatus
from app.modules.certificates import repository as certificates_repository
from app.modules.certifications import repository
from app.modules.certifications.schemas import (
    CertificationCardResponse,
    CertificationDetailResponse,
)
from app.modules.members import repository as members_repository
from app.modules.works import repository as works_repository

log = get_logger("certifications")

_ACTION_LABELS = {
    "under_review": "marked_under_review",
    "approve": "approved",
    "request_changes": "changes_requested",
    "reject": "rejected",
}


def member_display_name(member: Member | None, member_id: str) -> str:
    if member is None:
        return member_id
    return member.full_name or member.profile.display_name or member.member_id


async def _side_data(
    requests: list[CertificationRequest],
) -> tuple[dict[str, MemberWork], dict[str, str]]:
    """Batch-load works (for current version/title) and member display names.

    Works that no longer exist fall back to the frozen snapshot so a decided
    review stays viewable after the member deletes their work.
    """
    works = await works_repository.find_many_by_ids(
        [request.work_id for request in requests]
    )
    names: dict[str, str] = {}
    for request in requests:
        if request.member_id in names:
            continue
        member = await members_repository.find_by_id(request.member_id)
        names[request.member_id] = member_display_name(member, request.member_id)
    return works, names


def _work_view(request: CertificationRequest, work: MemberWork | None) -> tuple[str, str, int]:
    if work is not None:
        return work.title, work.slug, work.version
    return request.snapshot.title, request.snapshot.slug, request.snapshot_version


async def build_cards(
    requests: list[CertificationRequest],
) -> list[CertificationCardResponse]:
    works, names = await _side_data(requests)
    cards: list[CertificationCardResponse] = []
    for request in requests:
        title, slug, version = _work_view(request, works.get(request.work_id))
        cards.append(
            CertificationCardResponse.from_request(
                request,
                work_title=title,
                work_slug=slug,
                current_version=version,
                member_name=names[request.member_id],
            )
        )
    return cards


async def build_detail(request: CertificationRequest) -> CertificationDetailResponse:
    works, names = await _side_data([request])
    title, slug, version = _work_view(request, works.get(request.work_id))
    detail = CertificationDetailResponse.from_request(
        request,
        work_title=title,
        work_slug=slug,
        current_version=version,
        member_name=names[request.member_id],
    )
    certificate = await certificates_repository.find_by_request_id(request.id)
    if certificate is not None:
        detail.certificate = CertificateRef(
            certificate_id=certificate.certificate_id,
            status=certificate.status,
            issued_at=certificate.issued_at,
            email_status=certificate.email_status,
            work_title=certificate.work_title,
            revoked_at=certificate.revoked_at,
        )
    return detail


def _snapshot_of(work: MemberWork) -> CertificationSnapshot:
    return CertificationSnapshot(
        slug=work.slug,
        title=work.title,
        summary=work.summary,
        cover_media_id=work.cover_media_id,
        tags=work.tags,
        external_links=work.external_links,
        content=work.content,
    )


async def _load_owned_published_work(member: Member, work_id: str) -> MemberWork:
    work = await works_repository.find_by_id(work_id)
    if work is None or work.member_id != member.id:
        raise AppError(404, "WORK_NOT_FOUND", "Work was not found")
    if work.publication_status != WorkPublicationStatus.PUBLISHED:
        raise AppError(
            409,
            "WORK_NOT_PUBLISHED",
            "Only published works are eligible for certification review",
        )
    return work


async def apply_or_resubmit(member: Member, work_id: str) -> CertificationRequest:
    work = await _load_owned_published_work(member, work_id)
    existing = await repository.find_active_for_work(work_id)
    now = datetime.now(timezone.utc)

    if existing is not None:
        if existing.status in (
            CertificationStatus.SUBMITTED,
            CertificationStatus.UNDER_REVIEW,
        ):
            raise AppError(
                409,
                "CERTIFICATION_ALREADY_ACTIVE",
                "A certification review for this work is already in progress",
            )
        # changes_requested — resubmit the same request with a fresh snapshot.
        snapshot = _snapshot_of(work)
        decision = CertificationDecision(
            action="resubmitted",
            by=member.id,
            by_role="member",
            at=now,
            feedback=None,
        )
        updated = await repository.update_request(
            existing.id,
            {
                "status": CertificationStatus.SUBMITTED.value,
                "active": True,
                "snapshot": snapshot.model_dump(),
                "snapshot_version": work.version,
                "version_reviewed": work.version,
                "captured_at": now,
                "submitted_at": now,
                "decided_at": None,
                "decided_by": None,
                "decided_by_role": None,
                "latest_feedback": None,
            },
            decision=decision,
        )
        if updated is None:  # pragma: no cover - deleted concurrently
            raise AppError(404, "CERTIFICATION_NOT_FOUND", "Review request was not found")
        log.info(
            "Certification resubmitted request_id=%s work_id=%s version=%d",
            updated.id,
            work_id,
            work.version,
        )
        return updated

    snapshot = _snapshot_of(work)
    try:
        request = await repository.insert_request(
            work_id=work_id,
            member_id=member.id,
            snapshot=snapshot,
            snapshot_version=work.version,
            submitted_at=now,
        )
    except DuplicateKeyError as exc:  # pragma: no cover - active-index race
        raise AppError(
            409,
            "CERTIFICATION_ALREADY_ACTIVE",
            "A certification review for this work is already in progress",
        ) from exc
    log.info(
        "Certification submitted request_id=%s work_id=%s member_id=%s",
        request.id,
        work_id,
        member.member_id,
    )
    return request


async def list_for_member(
    member: Member,
    *,
    page: int,
    page_size: int,
    status: str | None,
) -> tuple[list[CertificationRequest], int]:
    query: dict = {"member_id": member.id}
    if status:
        _require_valid_status(status)
        query["status"] = status
    return await repository.list_requests(
        query=query,
        sort=[("submitted_at", -1)],
        skip=(page - 1) * page_size,
        limit=page_size,
    )


async def get_for_member(member: Member, request_id: str) -> CertificationRequest:
    request = await repository.find_by_id(request_id)
    if request is None or request.member_id != member.id:
        raise AppError(404, "CERTIFICATION_NOT_FOUND", "Review request was not found")
    return request


def _require_valid_status(status: str) -> None:
    if status not in {item.value for item in CertificationStatus}:
        raise AppError(422, "INVALID_STATUS", "Unknown certification status filter")


async def admin_list(
    *,
    page: int,
    page_size: int,
    status: str | None,
) -> tuple[list[CertificationRequest], int]:
    query: dict = {}
    if status:
        _require_valid_status(status)
        query["status"] = status
    return await repository.list_requests(
        query=query,
        sort=[("submitted_at", -1)],
        skip=(page - 1) * page_size,
        limit=page_size,
    )


async def admin_get(request_id: str) -> CertificationRequest:
    request = await repository.find_by_id(request_id)
    if request is None:
        raise AppError(404, "CERTIFICATION_NOT_FOUND", "Review request was not found")
    return request


def _ensure_action_allowed(
    request: CertificationRequest, action: str
) -> None:
    if request.status in TERMINAL_STATUSES:
        raise AppError(
            409,
            "CERTIFICATION_ALREADY_DECIDED",
            "This certification review has already been decided",
        )
    if action == "under_review" and request.status == CertificationStatus.CHANGES_REQUESTED:
        raise AppError(
            409,
            "CERTIFICATION_AWAITING_RESUBMIT",
            "The member must resubmit before this review can continue",
        )


async def decide(
    admin: Admin,
    request_id: str,
    *,
    action: str,
    feedback: str | None,
    by_role: str,
) -> CertificationRequest:
    request = await admin_get(request_id)
    _ensure_action_allowed(request, action)

    if action in ("request_changes", "reject") and not feedback:
        raise AppError(
            422,
            "FEEDBACK_REQUIRED",
            "Feedback is required when requesting changes or rejecting",
        )

    now = datetime.now(timezone.utc)
    fields: dict = {
        "decided_at": now,
        "decided_by": admin.id,
        "decided_by_role": by_role,
        "latest_feedback": feedback,
    }
    if action == "under_review":
        fields["status"] = CertificationStatus.UNDER_REVIEW.value
        fields["active"] = True
    elif action == "request_changes":
        fields["status"] = CertificationStatus.CHANGES_REQUESTED.value
        fields["active"] = True
    elif action == "approve":
        fields["status"] = CertificationStatus.APPROVED.value
        fields["active"] = False
    elif action == "reject":
        fields["status"] = CertificationStatus.REJECTED.value
        fields["active"] = False
    else:  # pragma: no cover - schema Literal guards this
        raise AppError(422, "INVALID_ACTION", "Unknown review action")

    decision = CertificationDecision(
        action=_ACTION_LABELS[action],
        by=admin.id,
        by_role=by_role,
        at=now,
        feedback=feedback,
    )
    updated = await repository.update_request(request_id, fields, decision=decision)
    if updated is None:  # pragma: no cover - deleted concurrently
        raise AppError(404, "CERTIFICATION_NOT_FOUND", "Review request was not found")
    log.info(
        "Certification %s request_id=%s by admin=%s",
        action,
        request_id,
        admin.id,
    )
    return updated