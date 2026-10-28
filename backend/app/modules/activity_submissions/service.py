"""Activity submissions service (programmes/hackathons, individual only).

Business rules enforced here (never only in the UI):

- A submission may only be authored by a **confirmed participant** of a
  *programme* or *hackathon*. Membership is resolved from the authoritative
  `activity_participations` record for the authenticated member — a client can
  never forge an author or submit against an activity they are not part of.
- New submissions are only accepted while the activity is published and its
  end date has not passed. An existing, not-yet-final submission may still be
  edited/resubmitted after that date so a student can act on admin feedback.
- A student has at most one **deliverable** per activity (enforced by a unique
  index); **progress updates** may be filed many times.
- Deliverables must provide every part the activity lists in
  `required_deliverables` — nothing more is demanded, nothing less is allowed.
- Attachments must be media the member owns.
- An author may edit and resubmit while the submission is `pending` or
  `changes_requested`; approved/rejected submissions are finalised. Every admin
  decision is appended to `review_history` — resubmitting never erases it.
"""

from __future__ import annotations

from datetime import date, datetime, timezone

from pymongo.errors import DuplicateKeyError

from app.core.errors import AppError
from app.models.activity import (
    Activity,
    ActivityParticipation,
    ActivityStatus,
    ActivityType,
    ParticipationStatus,
)
from app.models.activity_submission import (
    DELIVERABLE_DESCRIPTION,
    DELIVERABLE_DEMO_URL,
    DELIVERABLE_EVIDENCE_LINKS,
    DELIVERABLE_REPOSITORY_URL,
    MAX_REVISIONS,
    ActivitySubmission,
    ActivitySubmissionKind,
    ActivitySubmissionReviewEntry,
    ActivitySubmissionRevision,
    ActivitySubmissionStatus,
)
from app.models.admin import Admin
from app.models.member import Member
from app.modules.activities import repository as activities_repository
from app.modules.activity_submissions import repository
from app.modules.members import repository as members_repository

_CONFIRMED = ParticipationStatus.CONFIRMED
_WORKSPACE_TYPES = (ActivityType.PROGRAMME, ActivityType.HACKATHON)


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _today() -> date:
    return _now().date()


# ---------------------------------------------------------------------------
# Authorization
# ---------------------------------------------------------------------------
async def _workspace_participation(
    member: Member, activity_id: str
) -> tuple[Activity, ActivityParticipation]:
    """Resolve a programme/hackathon the member is a confirmed participant of.

    Raises 404 when the id is unknown or is not a programme/hackathon (no leak
    that it exists) and 403 when the member is not a confirmed participant.
    """
    activity = await activities_repository.find_activity_by_id(activity_id)
    if activity is None or activity.activity_type not in _WORKSPACE_TYPES:
        raise AppError(404, "ACTIVITY_NOT_FOUND", "Activity was not found")
    participation = await activities_repository.find_participation(
        activity.id, member.id
    )
    if participation is None or participation.status != _CONFIRMED:
        raise AppError(
            403,
            "NOT_A_PARTICIPANT",
            "You are not a confirmed participant of this activity",
        )
    return activity, participation


async def _workspace_participation_by_slug(
    member: Member, slug: str
) -> tuple[Activity, ActivityParticipation]:
    """Slug-addressed variant (member-facing URLs use the activity slug)."""
    activity = await activities_repository.find_activity_by_slug(slug)
    if activity is None or activity.activity_type not in _WORKSPACE_TYPES:
        raise AppError(404, "ACTIVITY_NOT_FOUND", "Activity was not found")
    participation = await activities_repository.find_participation(
        activity.id, member.id
    )
    if participation is None or participation.status != _CONFIRMED:
        raise AppError(
            403,
            "NOT_A_PARTICIPANT",
            "You are not a confirmed participant of this activity",
        )
    return activity, participation


async def _owned_or_404(member: Member, submission_id: str) -> ActivitySubmission:
    submission = await repository.find_by_id(submission_id)
    if submission is None or submission.member_id != member.id:
        # Same error whether missing or owned by someone else — never confirm
        # the existence of another member's submission.
        raise AppError(404, "SUBMISSION_NOT_FOUND", "Submission was not found")
    return submission


# ---------------------------------------------------------------------------
# Validation helpers
# ---------------------------------------------------------------------------
def _validate_required_deliverables(
    activity: Activity,
    *,
    description: str,
    repository_url: str | None,
    demo_url: str | None,
    evidence_links: list[str],
) -> None:
    """Enforce exactly the deliverable parts the activity asks for."""
    required = set(activity.required_deliverables or [])
    missing: list[str] = []
    if DELIVERABLE_DESCRIPTION in required and not description.strip():
        missing.append("a description")
    if DELIVERABLE_REPOSITORY_URL in required and not repository_url:
        missing.append("a repository URL")
    if DELIVERABLE_DEMO_URL in required and not demo_url:
        missing.append("a demo URL")
    if DELIVERABLE_EVIDENCE_LINKS in required and not evidence_links:
        missing.append("at least one evidence link")
    if missing:
        raise AppError(
            422,
            "MISSING_DELIVERABLE",
            "This activity requires " + ", ".join(missing),
        )


async def _validate_owned_media(member_id: str, media_ids: list[str]) -> None:
    """Every referenced media record must exist AND belong to the member."""
    distinct = list(dict.fromkeys(media_id for media_id in media_ids if media_id))
    if not distinct:
        return
    from app.modules.media import repository as media_repository
    from app.services.references import require_media_exist

    await require_media_exist(distinct)
    found = await media_repository.find_many_by_id(distinct)
    for media_id in distinct:
        media = found.get(media_id)
        if media is None or media.created_by != member_id:
            raise AppError(
                422,
                "MEDIA_NOT_OWNED",
                "Attached media does not exist or is not yours",
            )


def _submission_window_open(activity: Activity, today: date) -> bool:
    """Whether *new* submissions are currently accepted for this activity."""
    if activity.status != ActivityStatus.PUBLISHED:
        return False
    if activity.end_date is not None and today > activity.end_date:
        return False
    return True


# ---------------------------------------------------------------------------
# Member — submit / edit
# ---------------------------------------------------------------------------
async def create_submission(member: Member, payload) -> ActivitySubmission:
    """Create a submission for an activity the member participates in."""
    activity, _participation = await _workspace_participation(member, payload.activity_id)

    if not _submission_window_open(activity, _today()):
        raise AppError(
            409,
            "SUBMISSION_CLOSED",
            "Submissions for this activity are closed",
        )

    if payload.kind == ActivitySubmissionKind.DELIVERABLE:
        _validate_required_deliverables(
            activity,
            description=payload.description,
            repository_url=payload.repository_url,
            demo_url=payload.demo_url,
            evidence_links=payload.evidence_links or [],
        )
        await _validate_owned_media(member.id, payload.attachment_media_ids or [])

    if payload.client_request_id:
        existing = await repository.find_by_client_request(
            member.id, payload.client_request_id
        )
        if existing is not None:
            return existing

    try:
        return await repository.insert_submission(
            activity_id=activity.id,
            activity_slug=activity.slug,
            activity_title=activity.title,
            activity_type=activity.activity_type.value,
            member_id=member.id,
            member_readable_id=member.member_id,
            kind=payload.kind.value,
            title=payload.title,
            description=payload.description,
            repository_url=payload.repository_url,
            demo_url=payload.demo_url,
            evidence_links=payload.evidence_links or [],
            attachment_media_ids=payload.attachment_media_ids or [],
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
            409,
            "DUPLICATE_SUBMISSION",
            "You already have a deliverable for this activity",
        )


async def update_submission(member: Member, submission_id: str, payload) -> ActivitySubmission:
    """Edit and resubmit one of the member's own submissions."""
    submission = await _owned_or_404(member, submission_id)
    if not submission.is_editable:
        raise AppError(
            409,
            "SUBMISSION_FINALIZED",
            "This submission can no longer be edited",
        )

    activity, _participation = await _workspace_participation(
        member, submission.activity_id
    )

    if submission.kind == ActivitySubmissionKind.DELIVERABLE:
        _validate_required_deliverables(
            activity,
            description=payload.description,
            repository_url=payload.repository_url,
            demo_url=payload.demo_url,
            evidence_links=payload.evidence_links or [],
        )
        await _validate_owned_media(member.id, payload.attachment_media_ids or [])

    # Keep the previous content as a revision so the member keeps a history of
    # what they submitted (deliverables only — progress updates are individual
    # entries in the timeline).
    revision: dict | None = None
    if submission.kind == ActivitySubmissionKind.DELIVERABLE:
        revision = ActivitySubmissionRevision(
            version=submission.version,
            title=submission.title,
            description=submission.description,
            repository_url=submission.repository_url,
            demo_url=submission.demo_url,
            evidence_links=submission.evidence_links,
            attachment_media_ids=submission.attachment_media_ids,
            submitted_at=submission.submitted_at,
        ).model_dump()

    updated = await repository.update_submission(
        submission_id,
        {
            "title": payload.title,
            "description": payload.description,
            "repository_url": payload.repository_url,
            "demo_url": payload.demo_url,
            "evidence_links": payload.evidence_links or [],
            "attachment_media_ids": payload.attachment_media_ids or [],
            "status": ActivitySubmissionStatus.PENDING.value,
            "version": submission.version + 1,
        },
        revision=revision,
    )
    if updated is None:  # pragma: no cover - deleted concurrently
        raise AppError(404, "SUBMISSION_NOT_FOUND", "Submission was not found")
    return updated


async def list_my_submissions(
    member: Member, *, page: int, page_size: int
) -> tuple[list[ActivitySubmission], int]:
    return await repository.list_by_member(
        member_id=member.id, page=page, page_size=page_size
    )


async def get_my_submission(member: Member, submission_id: str) -> ActivitySubmission:
    return await _owned_or_404(member, submission_id)


# ---------------------------------------------------------------------------
# Member — workspace
# ---------------------------------------------------------------------------
def _progress_percent(completed: int, total: int) -> int:
    if total <= 0:
        return 0
    return int(round(completed / total * 100))


async def _workspace_response(
    member: Member,
    activity: Activity,
    participation: ActivityParticipation,
    *,
    deliverables: list[ActivitySubmission],
    progress_updates: list[ActivitySubmission],
) -> "object":
    """Build one member workspace payload (activity + personal progress)."""
    from app.modules.activity_submissions.schemas import (
        ActivityResourceResponse,
        ActivitySubmissionResponse,
        ActivityTaskResponse,
        ActivityWorkspaceResponse,
    )

    deliverable = next(
        (item for item in deliverables if item.kind == ActivitySubmissionKind.DELIVERABLE),
        None,
    )
    completed_ids = set(participation.completed_task_ids)
    tasks = [
        ActivityTaskResponse(
            id=task.id,
            title=task.title,
            description=task.description,
            due_date=task.due_date,
            completed=task.id in completed_ids,
        )
        for task in activity.tasks
    ]
    completed_count = sum(1 for task in tasks if task.completed)

    today = _today()
    window_open = _submission_window_open(activity, today)
    can_submit = window_open
    blocked_reason: str | None = None
    if not window_open:
        blocked_reason = (
            "This activity is not open for submissions."
            if activity.status != ActivityStatus.PUBLISHED
            else "The submission deadline for this activity has passed."
        )

    return ActivityWorkspaceResponse(
        activity_id=activity.id,
        slug=activity.slug,
        title=activity.title,
        activity_type=activity.activity_type.value,
        summary=activity.summary,
        description=activity.description,
        presentation_status=activity.presentation_status(today=today).value,
        start_date=activity.start_date,
        end_date=activity.end_date,
        banner_media_id=activity.banner_media_id,
        has_brief=activity.brief is not None,
        objectives=list(activity.objectives),
        instructions=activity.instructions,
        requirements=list(activity.requirements),
        resources=[
            ActivityResourceResponse(label=item.label, url=item.url)
            for item in activity.resources
        ],
        required_deliverables=list(activity.required_deliverables),
        participation_status=participation.status.value,
        participation_role=participation.role,
        tasks=tasks,
        completed_task_count=completed_count,
        task_count=len(tasks),
        progress_percent=_progress_percent(completed_count, len(tasks)),
        deliverable=(
            ActivitySubmissionResponse.from_submission(deliverable)
            if deliverable is not None
            else None
        ),
        progress_updates=[
            ActivitySubmissionResponse.from_submission(item)
            for item in progress_updates
        ],
        can_submit=can_submit,
        submit_blocked_reason=blocked_reason,
    )


async def list_my_workspaces(member: Member) -> list:
    """Every programme/hackathon the member is a confirmed participant of."""
    participations = await activities_repository.list_member_participations(member.id)
    confirmed = [p for p in participations if p.status == _CONFIRMED]
    if not confirmed:
        return []
    activity_map = await activities_repository.find_activities_by_ids(
        [p.activity_id for p in confirmed]
    )

    items = []
    for participation in confirmed:
        activity = activity_map.get(participation.activity_id)
        if activity is None or activity.activity_type not in _WORKSPACE_TYPES:
            continue
        submissions = await repository.list_by_member_and_activity(
            member_id=member.id, activity_id=activity.id
        )
        deliverables = [
            item
            for item in submissions
            if item.kind == ActivitySubmissionKind.DELIVERABLE
        ]
        progress_updates = [
            item
            for item in submissions
            if item.kind == ActivitySubmissionKind.PROGRESS_UPDATE
        ]
        items.append(
            await _workspace_response(
                member,
                activity,
                participation,
                deliverables=deliverables,
                progress_updates=progress_updates,
            )
        )
    items.sort(key=lambda item: (item.start_date or date.max, item.title.lower()))
    return items


async def get_my_workspace(member: Member, slug: str):
    """One member workspace (404 when not a participant of a programme/hackathon)."""
    activity, participation = await _workspace_participation_by_slug(member, slug)
    submissions = await repository.list_by_member_and_activity(
        member_id=member.id, activity_id=activity.id
    )
    deliverables = [
        item for item in submissions if item.kind == ActivitySubmissionKind.DELIVERABLE
    ]
    progress_updates = [
        item for item in submissions if item.kind == ActivitySubmissionKind.PROGRESS_UPDATE
    ]
    return await _workspace_response(
        member,
        activity,
        participation,
        deliverables=deliverables,
        progress_updates=progress_updates,
    )


async def set_task_completion(
    member: Member, slug: str, *, task_id: str, completed: bool
):
    """Toggle the member's own completion of one activity task."""
    activity, participation = await _workspace_participation_by_slug(member, slug)
    task_ids = {task.id for task in activity.tasks}
    if task_id not in task_ids:
        raise AppError(404, "TASK_NOT_FOUND", "Task was not found")

    current = list(participation.completed_task_ids)
    if completed and task_id not in current:
        current.append(task_id)
    elif not completed and task_id in current:
        current = [item for item in current if item != task_id]

    updated = await activities_repository.update_participation(
        participation.id, {"completed_task_ids": current}
    )
    if updated is None:  # pragma: no cover - deleted concurrently
        raise AppError(
            404, "PARTICIPATION_NOT_FOUND", "Participation record was not found"
        )
    return await get_my_workspace(member, activity.slug)


# ---------------------------------------------------------------------------
# Admin — review queue + decisions
# ---------------------------------------------------------------------------
async def list_for_admin(
    *,
    page: int,
    page_size: int,
    status: str | None,
    kind: str | None,
    activity_id: str | None,
    member_id: str | None,
) -> tuple[list[ActivitySubmission], int]:
    if status and status not in {item.value for item in ActivitySubmissionStatus}:
        raise AppError(422, "INVALID_STATUS", "Unknown submission status filter")
    if kind and kind not in {item.value for item in ActivitySubmissionKind}:
        raise AppError(422, "INVALID_KIND", "Unknown submission kind filter")
    if activity_id:
        activity = await activities_repository.find_activity_by_id(activity_id)
        if activity is None:
            raise AppError(404, "ACTIVITY_NOT_FOUND", "Activity was not found")
    return await repository.list_by_activity(
        activity_id=activity_id,
        page=page,
        page_size=page_size,
        status=status,
        kind=kind,
        member_id=member_id,
    )


async def get_for_admin(submission_id: str) -> ActivitySubmission:
    submission = await repository.find_by_id(submission_id)
    if submission is None:
        raise AppError(404, "SUBMISSION_NOT_FOUND", "Submission was not found")
    return submission


async def decide_submission(
    admin: Admin, submission_id: str, *, action: str, feedback: str | None
) -> ActivitySubmission:
    """Record an admin decision. Only a `pending` submission can be decided and
    `request_changes` requires feedback. The decision is appended to the review
    history (never overwriting earlier decisions)."""
    submission = await get_for_admin(submission_id)
    if submission.status != ActivitySubmissionStatus.PENDING:
        raise AppError(
            409, "SUBMISSION_NOT_IN_REVIEW", "This submission is not awaiting review"
        )
    if action == "request_changes" and not feedback:
        raise AppError(
            422,
            "FEEDBACK_REQUIRED",
            "Feedback is required when requesting changes",
        )

    now = _now()
    if action == "approve":
        new_status = ActivitySubmissionStatus.APPROVED
    elif action == "request_changes":
        new_status = ActivitySubmissionStatus.CHANGES_REQUESTED
    elif action == "reject":
        new_status = ActivitySubmissionStatus.REJECTED
    else:  # pragma: no cover - schema Literal guards this
        raise AppError(422, "INVALID_ACTION", "Unknown review action")

    entry = ActivitySubmissionReviewEntry(
        status=new_status,
        reviewer_id=admin.id,
        reviewer_name=admin.email,
        feedback=feedback,
        version=submission.version,
        decided_at=now,
    )
    updated = await repository.update_submission(
        submission_id,
        {
            "status": new_status.value,
            "reviewed_at": now,
            "reviewed_by": admin.id,
            "review_feedback": feedback,
        },
        review_entry=entry.model_dump(),
    )
    if updated is None:  # pragma: no cover - deleted concurrently
        raise AppError(404, "SUBMISSION_NOT_FOUND", "Submission was not found")
    return updated


async def admin_responses(
    submissions: list[ActivitySubmission],
) -> list:
    """Resolve author display names in a single batched lookup (no N+1)."""
    from app.modules.activity_submissions.schemas import (
        AdminActivitySubmissionResponse,
    )

    member_ids = list({item.member_id for item in submissions})
    members = await members_repository.find_many_by_ids(member_ids)
    out = []
    for submission in submissions:
        member = members.get(submission.member_id)
        name = (
            (member.full_name or member.profile.display_name or member.member_id)
            if member
            else submission.member_readable_id
        )
        out.append(
            AdminActivitySubmissionResponse.from_submission(
                submission,
                member_name=name,
                member_email=member.email if member else None,
            )
        )
    return out


async def get_student_activity(
    activity_id: str, member_id: str
):
    """One student's individual record inside one activity (admin view)."""
    from app.modules.activity_submissions.schemas import (
        ActivityTaskResponse,
        AdminStudentActivityResponse,
    )

    activity = await activities_repository.find_activity_by_id(activity_id)
    if activity is None:
        raise AppError(404, "ACTIVITY_NOT_FOUND", "Activity was not found")
    participation = await activities_repository.find_participation(activity.id, member_id)
    if participation is None:
        raise AppError(
            404, "PARTICIPATION_NOT_FOUND", "Participation record was not found"
        )

    submissions = await repository.list_by_member_and_activity(
        member_id=member_id, activity_id=activity.id
    )
    member = await members_repository.find_by_id(member_id)
    completed_ids = set(participation.completed_task_ids)
    tasks = [
        ActivityTaskResponse(
            id=task.id,
            title=task.title,
            description=task.description,
            due_date=task.due_date,
            completed=task.id in completed_ids,
        )
        for task in activity.tasks
    ]
    completed_count = sum(1 for task in tasks if task.completed)

    return AdminStudentActivityResponse(
        activity_id=activity.id,
        activity_slug=activity.slug,
        activity_title=activity.title,
        activity_type=activity.activity_type.value,
        member_id=member_id,
        member_readable_id=participation.member_readable_id,
        member_name=member.full_name if member else None,
        member_email=member.email if member else None,
        participation_status=participation.status.value,
        participation_role=participation.role,
        participation_source=participation.source.value,
        confirmed_at=participation.confirmed_at,
        tasks=tasks,
        completed_task_count=completed_count,
        task_count=len(tasks),
        progress_percent=_progress_percent(completed_count, len(tasks)),
        submissions=await admin_responses(submissions),
    )


__all__ = [
    "MAX_REVISIONS",
    "admin_responses",
    "create_submission",
    "decide_submission",
    "get_for_admin",
    "get_my_submission",
    "get_my_workspace",
    "get_student_activity",
    "list_for_admin",
    "list_my_submissions",
    "list_my_workspaces",
    "set_task_completion",
    "update_submission",
]
