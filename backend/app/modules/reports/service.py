"""Project Progress Reports service.

Business rules enforced here (never only in the UI):

- A report may only be authored by a **confirmed participant** of a *project*
  activity. Membership is resolved from the authoritative
  `activity_participations` record for the authenticated member — a client can
  never forge an author or submit against a project they are not part of.
- Descriptions are capped (500 characters) and evidence links must be http(s).
- Submission is idempotent per client-supplied request id, so a double-click or
  a retried request cannot create duplicate reports.
- An author may edit and resubmit a report while it is `pending` or
  `changes_requested`; an `approved` report is finalised. Every admin decision
  is appended to `review_history` — resubmitting never erases review history.
- Only `approved` reports are surfaced in the member's contribution history, and
  the history is scoped to the member's own session (never published publicly).
"""

from __future__ import annotations

import re
from datetime import datetime, timezone

from pymongo.errors import DuplicateKeyError

from app.core.errors import AppError
from app.models.activity import (
    Activity,
    ActivityParticipation,
    ActivityType,
    ParticipationStatus,
)
from app.models.admin import Admin
from app.models.member import Member
from app.models.progress_report import (
    ProgressReport,
    ReportReviewEntry,
    ReportStatus,
)
from app.modules.activities import repository as activities_repository
from app.modules.ai import repository as summaries_repository
from app.modules.members import repository as members_repository
from app.modules.reports import repository
from app.modules.reports.schemas import (
    AdminReportResponse,
    ContributionHistoryResponse,
    ContributionProjectGroup,
    ContributionReportResponse,
    ContributionSummaryResponse,
    MemberProjectSummary,
    ReportCreateRequest,
    ReportResponse,
    ReportUpdateRequest,
)

_CONFIRMED = ParticipationStatus.CONFIRMED
_PROJECT = ActivityType.PROJECT


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _today():
    return _now().date()


# ---------------------------------------------------------------------------
# Authorization
# ---------------------------------------------------------------------------
async def _project_participation(
    member: Member, activity_id: str
) -> tuple[Activity, ActivityParticipation]:
    """Resolve a project the member is a confirmed participant of.

    Raises 404 when the id is unknown/not a project (no leak that it exists) and
    403 when the project exists but the member is not a confirmed participant.
    """
    activity = await activities_repository.find_activity_by_id(activity_id)
    if activity is None or activity.activity_type != _PROJECT:
        raise AppError(404, "PROJECT_NOT_FOUND", "Project was not found")
    participation = await activities_repository.find_participation(
        activity.id, member.id
    )
    if participation is None or participation.status != _CONFIRMED:
        raise AppError(
            403,
            "NOT_A_PARTICIPANT",
            "You are not a confirmed participant of this project",
        )
    return activity, participation


async def _owned_or_404(member: Member, report_id: str) -> ProgressReport:
    report = await repository.find_by_id(report_id)
    if report is None or report.member_id != member.id:
        # Same error whether missing or owned by someone else — never confirm
        # the existence of another member's report.
        raise AppError(404, "REPORT_NOT_FOUND", "Report was not found")
    return report


# ---------------------------------------------------------------------------
# Member — submit / list / view / edit
# ---------------------------------------------------------------------------
async def create_report(member: Member, payload: ReportCreateRequest) -> ProgressReport:
    activity, participation = await _project_participation(member, payload.activity_id)

    if payload.client_request_id:
        existing = await repository.find_by_client_request(
            member.id, payload.client_request_id
        )
        if existing is not None:
            return existing

    try:
        return await repository.insert_report(
            activity_id=activity.id,
            activity_slug=activity.slug,
            activity_title=activity.title,
            member_id=member.id,
            member_readable_id=member.member_id,
            role=participation.role,
            description=payload.description,
            evidence_links=payload.evidence_links,
            client_request_id=payload.client_request_id,
        )
    except DuplicateKeyError:
        # Concurrent duplicate of the same idempotency key — return the winner.
        if payload.client_request_id:
            existing = await repository.find_by_client_request(
                member.id, payload.client_request_id
            )
            if existing is not None:
                return existing
        raise AppError(
            409, "DUPLICATE_REPORT", "This report was already submitted"
        )


async def list_my_reports(
    member: Member,
    *,
    activity_id: str | None,
    page: int,
    page_size: int,
) -> tuple[list[ProgressReport], int]:
    query: dict = {"member_id": member.id}
    if activity_id:
        query["activity_id"] = activity_id
    return await repository.list_reports(
        query=query,
        sort=[("submitted_at", -1)],
        skip=(page - 1) * page_size,
        limit=page_size,
    )


async def get_my_report(member: Member, report_id: str) -> ProgressReport:
    return await _owned_or_404(member, report_id)


async def edit_report(
    member: Member, report_id: str, payload: ReportUpdateRequest
) -> ProgressReport:
    report = await _owned_or_404(member, report_id)
    if report.status == ReportStatus.APPROVED:
        raise AppError(
            409, "REPORT_FINALIZED", "An approved report can no longer be edited"
        )
    # Resubmit: content replaced, version bumped, status returns to pending for
    # a fresh review. Prior review history is untouched.
    updated = await repository.update_report(
        report_id,
        {
            "description": payload.description,
            "evidence_links": payload.evidence_links,
            "status": ReportStatus.PENDING.value,
            "version": report.version + 1,
        },
    )
    if updated is None:  # pragma: no cover - deleted concurrently
        raise AppError(404, "REPORT_NOT_FOUND", "Report was not found")
    return updated


# ---------------------------------------------------------------------------
# Member — projects overview + contribution history
# ---------------------------------------------------------------------------
async def list_member_projects(member: Member) -> list[MemberProjectSummary]:
    participations = await activities_repository.list_member_participations(member.id)
    confirmed = [p for p in participations if p.status == _CONFIRMED]
    if not confirmed:
        return []
    activity_map = await activities_repository.find_activities_by_ids(
        [p.activity_id for p in confirmed]
    )
    counts = await repository.status_counts_by_activity(member.id)
    today = _today()

    items: list[MemberProjectSummary] = []
    for participation in confirmed:
        activity = activity_map.get(participation.activity_id)
        if activity is None or activity.activity_type != _PROJECT:
            continue
        stats = counts.get(activity.id, {})
        items.append(
            MemberProjectSummary(
                activity_id=activity.id,
                slug=activity.slug,
                title=activity.title,
                role=participation.role,
                presentation_status=activity.presentation_status(today=today),
                start_date=activity.start_date,
                end_date=activity.end_date,
                banner_media_id=activity.banner_media_id,
                report_count=int(stats.get("total", 0)),
                pending_count=int(stats.get("pending", 0)),
                changes_requested_count=int(stats.get("changes_requested", 0)),
                approved_count=int(stats.get("approved", 0)),
                last_report_at=stats.get("last_report_at"),
            )
        )
    items.sort(key=lambda r: (r.last_report_at is None, r.title.lower()))
    return items


async def contribution_history(member: Member) -> ContributionHistoryResponse:
    """The member's official contribution history: `approved` reports grouped by
    project, newest project first, reports chronological within a project.

    Any *published* AI work summary for a project is attached to that project's
    group. Drafts are never surfaced, and a summary's underlying approved reports
    remain listed as the evidence it was drawn from.
    """
    reports = await repository.find_all(
        {"member_id": member.id, "status": ReportStatus.APPROVED.value},
        sort=[("submitted_at", 1)],
        limit=2000,
    )
    published = await summaries_repository.find_published_for_member(member.id)

    if not reports and not published:
        return ContributionHistoryResponse(items=[], total_reports=0)

    activity_ids = list(
        {report.activity_id for report in reports}
        | {summary.activity_id for summary in published}
    )
    activity_map = await activities_repository.find_activities_by_ids(activity_ids)
    participations = await activities_repository.list_member_participations(member.id)
    role_map = {p.activity_id: p.role for p in participations}

    grouped: dict[str, list[ProgressReport]] = {}
    for report in reports:
        grouped.setdefault(report.activity_id, []).append(report)

    summaries_by_activity: dict[str, list] = {}
    for summary in published:
        summaries_by_activity.setdefault(summary.activity_id, []).append(summary)

    items: list[ContributionProjectGroup] = []
    for activity_id in grouped.keys() | summaries_by_activity.keys():
        activity = activity_map.get(activity_id)
        if activity is None:
            continue
        group_reports = grouped.get(activity_id, [])
        group_summaries = summaries_by_activity.get(activity_id, [])
        items.append(
            ContributionProjectGroup(
                activity_id=activity.id,
                slug=activity.slug,
                title=activity.title,
                role=role_map.get(
                    activity.id,
                    group_reports[0].role if group_reports else None,
                ),
                report_count=len(group_reports),
                reports=[
                    ContributionReportResponse(
                        id=report.id,
                        description=report.description,
                        evidence_links=report.evidence_links,
                        approved_at=report.reviewed_at or report.updated_at,
                        submitted_at=report.submitted_at,
                    )
                    for report in group_reports
                ],
                summaries=[
                    ContributionSummaryResponse(
                        id=summary.id,
                        content=summary.published_content or "",
                        model=summary.published_model,
                        published_at=summary.published_at,
                        source_report_count=len(summary.published_source_reports),
                        source_report_ids=[
                            ref.report_id for ref in summary.published_source_reports
                        ],
                    )
                    for summary in group_summaries
                    if summary.published_at is not None
                ],
            )
        )
    # Newest-contributing project first (by latest report or summary date).
    def _recency(group: ContributionProjectGroup):
        stamps = [report.approved_at for report in group.reports]
        stamps += [summary.published_at for summary in group.summaries]
        return max(stamps)

    items.sort(key=_recency, reverse=True)
    return ContributionHistoryResponse(items=items, total_reports=len(reports))


# ---------------------------------------------------------------------------
# Admin — review queue + decisions
# ---------------------------------------------------------------------------
async def _search_clause(search: str) -> dict | None:
    """Build an $or clause matching reports by author (name/email/id) or project
    title. Returns None when nothing matches."""
    pattern = re.escape(search.strip())
    member_ids = await members_repository.search_member_ids(pattern)
    activity_ids = await activities_repository.search_activity_ids(pattern)
    clauses: list[dict] = []
    if member_ids:
        clauses.append({"member_id": {"$in": member_ids}})
    if activity_ids:
        clauses.append({"activity_id": {"$in": activity_ids}})
    if not clauses:
        return {"_id": None}  # matches nothing
    return {"$or": clauses}


async def list_for_admin(
    *,
    page: int,
    page_size: int,
    status: str | None,
    activity_id: str | None,
    member_id: str | None,
    search: str | None,
    sort: list[tuple],
) -> tuple[list[ProgressReport], int]:
    query: dict = {}
    if status:
        if status not in {item.value for item in ReportStatus}:
            raise AppError(422, "INVALID_STATUS", "Unknown report status filter")
        query["status"] = status
    if activity_id:
        query["activity_id"] = activity_id
    if member_id:
        query["member_id"] = member_id
    if search and search.strip():
        clause = await _search_clause(search)
        if clause is not None:
            query.update(clause)
    return await repository.list_reports(
        query=query, sort=sort, skip=(page - 1) * page_size, limit=page_size
    )


async def get_for_admin(report_id: str) -> ProgressReport:
    report = await repository.find_by_id(report_id)
    if report is None:
        raise AppError(404, "REPORT_NOT_FOUND", "Report was not found")
    return report


async def decide_report(
    admin: Admin,
    report_id: str,
    *,
    action: str,
    feedback: str | None,
) -> ProgressReport:
    """Record an admin decision. Only a `pending` report can be decided;
    `request_changes` requires feedback. The decision is appended to the review
    history (never overwriting earlier decisions)."""
    report = await get_for_admin(report_id)
    if report.status != ReportStatus.PENDING:
        raise AppError(
            409, "REPORT_NOT_IN_REVIEW", "This report is not awaiting review"
        )
    if action == "request_changes" and not feedback:
        raise AppError(
            422,
            "FEEDBACK_REQUIRED",
            "Feedback is required when requesting changes",
        )

    now = _now()
    if action == "approve":
        new_status = ReportStatus.APPROVED
    elif action == "request_changes":
        new_status = ReportStatus.CHANGES_REQUESTED
    else:  # pragma: no cover - schema Literal guards this
        raise AppError(422, "INVALID_ACTION", "Unknown review action")

    entry = ReportReviewEntry(
        status=new_status,
        reviewer_id=admin.id,
        reviewer_name=admin.email,
        feedback=feedback,
        version=report.version,
        decided_at=now,
    )
    updated = await repository.update_report(
        report_id,
        {
            "status": new_status.value,
            "reviewed_at": now,
            "reviewed_by": admin.id,
            "review_feedback": feedback,
        },
        review_entry=entry,
    )
    if updated is None:  # pragma: no cover - deleted concurrently
        raise AppError(404, "REPORT_NOT_FOUND", "Report was not found")
    return updated


# ---------------------------------------------------------------------------
# Response builders
# ---------------------------------------------------------------------------
async def member_responses(
    reports: list[ProgressReport],
) -> list[ReportResponse]:
    return [ReportResponse.from_report(report) for report in reports]


async def admin_responses(
    reports: list[ProgressReport],
) -> list[AdminReportResponse]:
    """Resolve author display names in a single batched lookup (no N+1)."""
    member_ids = list({report.member_id for report in reports})
    members = await members_repository.find_many_by_ids(member_ids)
    out: list[AdminReportResponse] = []
    for report in reports:
        member = members.get(report.member_id)
        name = (
            (member.full_name or member.profile.display_name or member.member_id)
            if member
            else report.member_readable_id
        )
        out.append(
            AdminReportResponse.from_report(
                report,
                member_name=name,
                member_email=member.email if member else None,
            )
        )
    return out
