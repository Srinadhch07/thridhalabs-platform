"""Activities service: lifecycle, brief versioning, project invitations +
emails, participation records and open self-registration.

Business rules enforced here (never only in the UI):

- Only `published` activities are listed publicly; a `cancelled` activity stays
  reachable by slug (clearly marked) but is never listed or promoted; drafts and
  archived activities are never public.
- Project invitations are only sent for `published` projects, and sending an
  invitation never by itself confirms a member — an admin confirms explicitly.
- Open registration (programme/hackathon) is duplicate-safe: the unique
  (activity, member) index is the real guard, with a friendly 409 on top.
- Replacing a brief appends an immutable version; the active participant's
  agreed obligation is never silently rewritten.
"""

from __future__ import annotations

from datetime import date, datetime, timezone

from pymongo.errors import DuplicateKeyError

from app.core.bson import serialize_for_mongo
from app.core.config import get_settings
from app.core.errors import AppError
from app.core.logging import get_logger
from app.core.slugs import slugify, validate_slug
from app.models.activity import (
    Activity,
    ActivityBriefVersion,
    ActivityParticipation,
    ActivityStatus,
    ActivityType,
    ParticipationSource,
    ParticipationStatus,
)
from app.models.member import Member, MemberStatus
from app.modules.activities import repository
from app.modules.activities import pdf as pdf_module
from app.modules.activities.schemas import (
    ActivityAdminResponse,
    ActivityCreate,
    ActivityPublicResponse,
    ActivityUpdate,
    BriefResponse,
    InvitationRequest,
    InvitationResult,
    MemberActivityResponse,
    ParticipantResponse,
    ParticipantUpdateRequest,
)
from app.modules.members import repository as members_repository
from app.services.email import EmailDeliveryError, send_email
from app.services.references import require_media_exist

log = get_logger("activities")

# Fields that may legitimately be cleared back to null by an explicit update.
_NULLABLE_UPDATE_KEYS = {
    "banner_media_id",
    "start_date",
    "end_date",
    "cancel_reason",
    "summary",
    "description",
    "roles_offered",
    "tags",
    "objectives",
    "instructions",
    "requirements",
    "resources",
    "tasks",
    "required_deliverables",
}

_CONFIRMED = ParticipationStatus.CONFIRMED.value


def _today() -> date:
    return datetime.now(timezone.utc).date()


def _now() -> datetime:
    return datetime.now(timezone.utc)


# ---------------------------------------------------------------------------
# Slug + lifecycle helpers
# ---------------------------------------------------------------------------
async def _generate_unique_slug(title: str) -> str:
    base = slugify(title)
    if not base:
        raise AppError(
            422,
            "INVALID_SLUG",
            "Cannot generate a slug from this title; provide a slug explicitly",
        )
    candidate = base
    counter = 2
    while await repository.find_activity_by_slug(candidate) is not None:
        candidate = f"{base}-{counter}"
        counter += 1
    return candidate


def _status_fields(new_status: ActivityStatus, current: ActivityStatus) -> dict:
    """Set/keep lifecycle timestamps on a status transition."""
    fields: dict = {}
    if new_status == ActivityStatus.PUBLISHED and current != ActivityStatus.PUBLISHED:
        fields["published_at"] = _now()
    if new_status == ActivityStatus.CANCELLED and current != ActivityStatus.CANCELLED:
        fields["cancelled_at"] = _now()
    if new_status == ActivityStatus.ARCHIVED and current != ActivityStatus.ARCHIVED:
        fields["archived_at"] = _now()
    return fields


async def _require_activity(activity_id: str) -> Activity:
    activity = await repository.find_activity_by_id(activity_id)
    if activity is None:
        raise AppError(404, "ACTIVITY_NOT_FOUND", "Activity was not found")
    return activity


# ---------------------------------------------------------------------------
# CRUD
# ---------------------------------------------------------------------------
async def create_activity(payload: ActivityCreate, *, admin_id: str) -> Activity:
    data = serialize_for_mongo(payload.model_dump(exclude_unset=True))
    await require_media_exist([data.get("banner_media_id")] if data.get("banner_media_id") else [])

    slug = data.get("slug")
    if slug:
        slug = validate_slug(slug)
        if await repository.find_activity_by_slug(slug) is not None:
            raise AppError(409, "SLUG_TAKEN", "An activity with this slug already exists")
    else:
        slug = await _generate_unique_slug(data["title"])

    status = ActivityStatus(data.get("status", ActivityStatus.DRAFT.value))
    lifecycle = _status_fields(status, ActivityStatus.DRAFT)

    insert_data = {
        key: value for key, value in data.items() if key not in ("title", "slug")
    }
    insert_data.update(lifecycle)
    insert_data["created_by"] = admin_id
    try:
        return await repository.insert_activity(title=data["title"], slug=slug, **insert_data)
    except DuplicateKeyError:
        raise AppError(409, "SLUG_TAKEN", "An activity with this slug already exists")


async def update_activity(activity_id: str, payload: ActivityUpdate) -> Activity:
    existing = await _require_activity(activity_id)
    data = serialize_for_mongo(payload.model_dump(exclude_unset=True))

    if "banner_media_id" in data and data.get("banner_media_id"):
        await require_media_exist([data["banner_media_id"]])

    if "slug" in data:
        if data["slug"] is None:
            raise AppError(422, "INVALID_SLUG", "Slug cannot be cleared")
        new_slug = validate_slug(data["slug"])
        if new_slug != existing.slug:
            other = await repository.find_activity_by_slug(new_slug)
            if other is not None and other.id != activity_id:
                raise AppError(409, "SLUG_TAKEN", "An activity with this slug already exists")
        data["slug"] = new_slug

    fields: dict = {}
    for key, value in data.items():
        if value is not None or key in _NULLABLE_UPDATE_KEYS:
            fields[key] = value

    # Validate the resulting date window (either side may be updated alone).
    start = fields.get("start_date", existing.start_date)
    end = fields.get("end_date", existing.end_date)
    if start is not None and end is not None and end < start:
        raise AppError(422, "INVALID_DATES", "end_date must not be before start_date")

    if "status" in data:
        new_status = ActivityStatus(data["status"])
        fields.update(_status_fields(new_status, existing.status))

    updated = await repository.update_activity(activity_id, fields)
    if updated is None:
        raise AppError(404, "ACTIVITY_NOT_FOUND", "Activity was not found")
    return updated


async def delete_activity(activity_id: str) -> None:
    await _require_activity(activity_id)
    await repository.delete_participations_for_activity(activity_id)
    await repository.delete_activity(activity_id)


async def list_admin(
    *, page: int, page_size: int, query: dict, sort: list[tuple]
) -> tuple[list[Activity], dict[str, dict[str, int]], int]:
    activities, total = await repository.list_activities(
        query=query, sort=sort, skip=(page - 1) * page_size, limit=page_size
    )
    counts = await repository.participation_counts([a.id for a in activities])
    return activities, counts, total


async def get_admin(activity_id: str) -> tuple[Activity, dict[str, int]]:
    """Load an activity (404 when missing) plus its participation counts."""
    activity = await _require_activity(activity_id)
    counts = await repository.participation_counts([activity.id])
    return activity, counts.get(activity.id, {})


async def get_activity(activity_id: str) -> Activity:
    """Load an activity or raise 404."""
    return await _require_activity(activity_id)


# ---------------------------------------------------------------------------
# PDF brief (versioned)
# ---------------------------------------------------------------------------
async def upload_brief(
    activity_id: str, *, admin_id: str, data: bytes, filename: str | None
) -> Activity:
    activity = await _require_activity(activity_id)
    settings = get_settings()
    pdf_module.validate_pdf_bytes(data, max_bytes=settings.ACTIVITY_BRIEF_MAX_BYTES)

    version = len(activity.brief_versions) + 1
    object_key = pdf_module.brief_object_key(activity.id, version)
    await pdf_module.store_brief(object_key, data)

    revision = ActivityBriefVersion(
        version=version,
        object_key=object_key,
        filename=pdf_module.safe_filename(filename),
        size_bytes=len(data),
        checksum=pdf_module.pdf_checksum(data),
        uploaded_by=admin_id,
        uploaded_at=_now(),
    )
    updated = await repository.append_brief_version(activity_id, version=revision)
    if updated is None:
        raise AppError(404, "ACTIVITY_NOT_FOUND", "Activity was not found")
    return updated


async def remove_brief(activity_id: str) -> Activity:
    await _require_activity(activity_id)
    updated = await repository.clear_brief(activity_id)
    if updated is None:
        raise AppError(404, "ACTIVITY_NOT_FOUND", "Activity was not found")
    return updated


async def read_brief_file(activity: Activity) -> tuple[bytes, str, str]:
    """Return (bytes, filename, mime) for the activity's current brief."""
    if activity.brief is None:
        raise AppError(404, "BRIEF_NOT_FOUND", "This activity has no brief")
    data = await pdf_module.read_brief(activity.brief.object_key)
    return data, activity.brief.filename, activity.brief.mime_type


# ---------------------------------------------------------------------------
# Invitations + participation
# ---------------------------------------------------------------------------
def _invitation_body(
    activity: Activity,
    member: Member,
    role: str | None,
    custom_message: str | None,
    contact_email: str | None,
) -> str:
    base = get_settings().FRONTEND_URL or ""
    link = f"{base.rstrip('/')}/activities/{activity.slug}" if base else ""
    lines = [
        f"Hello {member.full_name or member.member_id},",
        "",
        f"You are invited to participate in the project \"{activity.title}\" at "
        "Thridha Labs.",
    ]
    if role:
        lines.append(f"Proposed role: {role}.")
    window = ""
    if activity.start_date and activity.end_date:
        window = f"{activity.start_date} to {activity.end_date}"
    elif activity.start_date:
        window = f"starting {activity.start_date}"
    elif activity.end_date:
        window = f"until {activity.end_date}"
    if window:
        lines.append(f"Schedule: {window}.")
    if custom_message:
        lines.extend(["", custom_message.strip()])
    lines.append("")
    if link:
        lines.append(f"Details: {link}")
    lines.append(
        "Please reply to this email to express your interest; a coordinator will "
        "confirm your participation."
    )
    if contact_email:
        lines.append(f"Questions? {contact_email}")
    return "\n".join(lines) + "\n"


async def _contact_email() -> str | None:
    """Best-effort contact email for invitation footers (never fatal)."""
    try:
        from app.modules.settings import service as settings_service

        settings = await settings_service.get_settings()
        return settings.contact.contact_email
    except Exception:  # pragma: no cover - defensive
        return None


async def send_invitations(
    activity_id: str, payload: InvitationRequest
) -> InvitationResult:
    activity = await _require_activity(activity_id)
    if activity.activity_type != ActivityType.PROJECT:
        raise AppError(
            409,
            "NOT_A_PROJECT",
            "Invitations are only available for projects",
        )
    if activity.status != ActivityStatus.PUBLISHED:
        raise AppError(
            409,
            "ACTIVITY_NOT_PUBLISHED",
            "Publish the project before sending invitations",
        )

    invited = re_invited = emails_sent = email_failures = 0
    skipped: list[str] = []
    errors: list[str] = []
    contact_email = await _contact_email()

    seen: set[str] = set()
    for item in payload.invitations:
        if item.member_id in seen:
            continue
        seen.add(item.member_id)

        member = await members_repository.find_by_id(item.member_id)
        if member is None:
            errors.append("One invitation referenced an unknown member and was skipped")
            continue
        if member.status == MemberStatus.INACTIVE:
            skipped.append(member.member_id)
            continue

        existing = await repository.find_participation(activity.id, member.id)
        role = item.role.strip() if item.role else None
        now = _now()

        if existing is None:
            participation = await repository.insert_participation(
                activity_id=activity.id,
                member_id=member.id,
                member_readable_id=member.member_id,
                role=role,
                status=ParticipationStatus.INVITED.value,
                source=ParticipationSource.INVITED.value,
                invited_at=now,
            )
            invited += 1
        elif existing.status == ParticipationStatus.CONFIRMED:
            skipped.append(member.member_id)
            continue
        else:
            participation = await repository.update_participation(
                existing.id,
                {
                    "status": ParticipationStatus.INVITED.value,
                    "source": ParticipationSource.INVITED.value,
                    "role": role,
                    "invited_at": now,
                    "withdrawn_at": None,
                    "responded_at": None,
                },
            )
            re_invited += 1
            if participation is None:  # pragma: no cover - race
                continue

        body = _invitation_body(activity, member, role, payload.message, contact_email)
        subject = payload.subject or f"Invitation: {activity.title}"
        try:
            await send_email(to=member.email, subject=subject, text=body)
        except EmailDeliveryError:
            email_failures += 1
            errors.append(f"Could not email {member.member_id}")
            log.warning("Invitation email failed for member %s", member.member_id)
        else:
            emails_sent += 1
            await repository.update_participation(
                participation.id, {"email_sent_at": _now()}
            )

    return InvitationResult(
        invited=invited,
        re_invited=re_invited,
        emails_sent=emails_sent,
        email_failures=email_failures,
        skipped=skipped,
        errors=errors,
    )


async def list_participants(
    *, activity_id: str, page: int, page_size: int, status: str | None
) -> tuple[list[ActivityParticipation], int]:
    await _require_activity(activity_id)
    query: dict = {"activity_id": activity_id}
    if status:
        query["status"] = status
    return await repository.list_participations(
        query=query,
        sort=[("created_at", -1)],
        skip=(page - 1) * page_size,
        limit=page_size,
    )


async def update_participant(
    activity_id: str, participation_id: str, payload: ParticipantUpdateRequest
) -> ActivityParticipation:
    await _require_activity(activity_id)
    participation = await repository.find_participation_by_id(participation_id)
    if participation is None or participation.activity_id != activity_id:
        raise AppError(404, "PARTICIPATION_NOT_FOUND", "Participant record was not found")

    data = payload.model_dump(exclude_unset=True)
    fields: dict = {}
    if "role" in data:
        fields["role"] = (data["role"] or "").strip() or None
    if "note" in data:
        fields["note"] = (data["note"] or "").strip() or None
    if "status" in data and data["status"] is not None:
        new_status = ParticipationStatus(data["status"])
        fields["status"] = new_status.value
        now = _now()
        if new_status == ParticipationStatus.CONFIRMED:
            fields["confirmed_at"] = now
            fields["withdrawn_at"] = None
            fields["responded_at"] = now
        elif new_status in (ParticipationStatus.INTERESTED, ParticipationStatus.DECLINED):
            fields["responded_at"] = now
        elif new_status == ParticipationStatus.WITHDRAWN:
            fields["withdrawn_at"] = now

    updated = await repository.update_participation(participation_id, fields)
    if updated is None:
        raise AppError(404, "PARTICIPATION_NOT_FOUND", "Participant record was not found")
    return updated


# ---------------------------------------------------------------------------
# Public
# ---------------------------------------------------------------------------
async def list_public(
    *,
    page: int,
    page_size: int,
    activity_type: str | None,
    featured: bool | None,
    sort: list[tuple],
) -> tuple[list[Activity], int]:
    query: dict = {"status": ActivityStatus.PUBLISHED.value}
    if activity_type:
        query["activity_type"] = activity_type
    if featured is not None:
        query["featured"] = featured
    return await repository.list_activities(
        query=query, sort=sort, skip=(page - 1) * page_size, limit=page_size
    )


async def get_public_by_slug(slug: str) -> Activity:
    activity = await repository.find_activity_by_slug(slug)
    # A cancelled activity stays reachable so it can be seen as cancelled;
    # drafts and archived activities are never public.
    if activity is None or activity.status not in (
        ActivityStatus.PUBLISHED,
        ActivityStatus.CANCELLED,
    ):
        raise AppError(404, "ACTIVITY_NOT_FOUND", "Activity was not found")
    return activity


# ---------------------------------------------------------------------------
# Member self-service
# ---------------------------------------------------------------------------
async def _member_participation_map(member: Member) -> dict[str, ActivityParticipation]:
    participations = await repository.list_member_participations(member.id)
    return {p.activity_id: p for p in participations}


async def list_member_activities(member: Member) -> list[MemberActivityResponse]:
    today = _today()
    pmap = await _member_participation_map(member)

    # Published open activities the member could join.
    open_activities, _total = await repository.list_activities(
        query={
            "status": ActivityStatus.PUBLISHED.value,
            "activity_type": {
                "$in": [ActivityType.PROGRAMME.value, ActivityType.HACKATHON.value]
            },
        },
        sort=[("display_order", 1), ("created_at", -1)],
        skip=0,
        limit=200,
    )

    merged: dict[str, Activity] = {a.id: a for a in open_activities}
    # Include activities the member is involved in (e.g. project invitations).
    missing = [aid for aid in pmap if aid not in merged]
    if missing:
        for aid, activity in (await repository.find_activities_by_ids(missing)).items():
            merged[aid] = activity

    items: list[MemberActivityResponse] = []
    for activity in merged.values():
        participation = pmap.get(activity.id)
        items.append(_member_activity(activity, participation, today))
    items.sort(
        key=lambda r: (
            0 if r.participation_status else 1,
            r.start_date or date.max,
            r.slug,
        )
    )
    return items


def _member_activity(
    activity: Activity,
    participation: ActivityParticipation | None,
    today: date,
) -> MemberActivityResponse:
    registration_open = activity.registration_open(today=today)
    can_register = registration_open and (
        participation is None or participation.status == ParticipationStatus.WITHDRAWN
    )
    can_withdraw = bool(
        participation
        and participation.source == ParticipationSource.SELF_REGISTERED
        and participation.status == ParticipationStatus.CONFIRMED
    )
    return MemberActivityResponse(
        slug=activity.slug,
        title=activity.title,
        activity_type=activity.activity_type,
        summary=activity.summary,
        presentation_status=activity.presentation_status(today=today),
        start_date=activity.start_date,
        end_date=activity.end_date,
        banner_media_id=activity.banner_media_id,
        has_brief=activity.brief is not None,
        registration_open=registration_open,
        can_register=can_register,
        can_withdraw=can_withdraw,
        participation_status=participation.status if participation else None,
        participation_role=participation.role if participation else None,
    )


async def register(member: Member, slug: str) -> ActivityParticipation:
    activity = await repository.find_activity_by_slug(slug)
    if activity is None or activity.status != ActivityStatus.PUBLISHED:
        raise AppError(404, "ACTIVITY_NOT_FOUND", "Activity was not found")
    if not activity.is_open_registration:
        raise AppError(403, "INVITATION_ONLY", "This activity is invitation-only")
    if not activity.registration_open(today=_today()):
        raise AppError(
            409, "REGISTRATION_CLOSED", "Registration for this activity is closed"
        )

    existing = await repository.find_participation(activity.id, member.id)
    now = _now()
    if existing is not None and existing.status != ParticipationStatus.WITHDRAWN:
        raise AppError(
            409, "ALREADY_REGISTERED", "You are already registered for this activity"
        )
    try:
        if existing is not None:
            updated = await repository.update_participation(
                existing.id,
                {
                    "status": ParticipationStatus.CONFIRMED.value,
                    "source": ParticipationSource.SELF_REGISTERED.value,
                    "confirmed_at": now,
                    "withdrawn_at": None,
                },
            )
            if updated is None:  # pragma: no cover - race
                raise AppError(404, "ACTIVITY_NOT_FOUND", "Activity was not found")
            return updated
        return await repository.insert_participation(
            activity_id=activity.id,
            member_id=member.id,
            member_readable_id=member.member_id,
            status=ParticipationStatus.CONFIRMED.value,
            source=ParticipationSource.SELF_REGISTERED.value,
            confirmed_at=now,
        )
    except DuplicateKeyError:
        raise AppError(
            409, "ALREADY_REGISTERED", "You are already registered for this activity"
        )


async def get_member_activity(member: Member, slug: str) -> MemberActivityResponse:
    """Current view of one published activity for a member (post-action)."""
    activity = await repository.find_activity_by_slug(slug)
    if activity is None or activity.status != ActivityStatus.PUBLISHED:
        raise AppError(404, "ACTIVITY_NOT_FOUND", "Activity was not found")
    participation = await repository.find_participation(activity.id, member.id)
    return _member_activity(activity, participation, _today())


async def withdraw(member: Member, slug: str) -> ActivityParticipation:
    activity = await repository.find_activity_by_slug(slug)
    if activity is None:
        raise AppError(404, "ACTIVITY_NOT_FOUND", "Activity was not found")
    participation = await repository.find_participation(activity.id, member.id)
    if participation is None:
        raise AppError(404, "NOT_REGISTERED", "You are not registered for this activity")
    if (
        participation.source != ParticipationSource.SELF_REGISTERED
        or participation.status != ParticipationStatus.CONFIRMED
    ):
        raise AppError(
            409,
            "CANNOT_WITHDRAW",
            "This registration cannot be withdrawn here",
        )
    updated = await repository.update_participation(
        participation.id,
        {
            "status": ParticipationStatus.WITHDRAWN.value,
            "withdrawn_at": _now(),
        },
    )
    if updated is None:  # pragma: no cover - race
        raise AppError(404, "NOT_REGISTERED", "You are not registered for this activity")
    return updated


# ---------------------------------------------------------------------------
# Response builders
# ---------------------------------------------------------------------------
def to_admin_response(
    activity: Activity, counts: dict[str, int] | None = None
) -> ActivityAdminResponse:
    brief = (
        BriefResponse(
            version=activity.brief.version,
            filename=activity.brief.filename,
            size_bytes=activity.brief.size_bytes,
            uploaded_at=activity.brief.uploaded_at,
        )
        if activity.brief
        else None
    )
    return ActivityAdminResponse(
        id=activity.id,
        title=activity.title,
        slug=activity.slug,
        activity_type=activity.activity_type,
        summary=activity.summary,
        description=activity.description,
        status=activity.status,
        presentation_status=activity.presentation_status(today=_today()),
        start_date=activity.start_date,
        end_date=activity.end_date,
        banner_media_id=activity.banner_media_id,
        featured=activity.featured,
        display_order=activity.display_order,
        roles_offered=activity.roles_offered,
        tags=activity.tags,
        objectives=list(activity.objectives),
        instructions=activity.instructions,
        requirements=list(activity.requirements),
        resources=[item.model_dump() for item in activity.resources],
        tasks=[item.model_dump() for item in activity.tasks],
        required_deliverables=list(activity.required_deliverables),
        brief=brief,
        brief_history_count=len(activity.brief_versions),
        cancel_reason=activity.cancel_reason,
        participant_counts=counts or {},
        created_at=activity.created_at,
        updated_at=activity.updated_at,
        published_at=activity.published_at,
        cancelled_at=activity.cancelled_at,
        archived_at=activity.archived_at,
    )


def to_public_response(activity: Activity) -> ActivityPublicResponse:
    today = _today()
    return ActivityPublicResponse(
        slug=activity.slug,
        title=activity.title,
        activity_type=activity.activity_type,
        summary=activity.summary,
        description=activity.description,
        presentation_status=activity.presentation_status(today=today),
        start_date=activity.start_date,
        end_date=activity.end_date,
        banner_media_id=activity.banner_media_id,
        featured=activity.featured,
        display_order=activity.display_order,
        roles_offered=activity.roles_offered,
        tags=activity.tags,
        has_brief=activity.brief is not None,
        registration_open=activity.registration_open(today=today),
    )


async def to_participant_response(
    participation: ActivityParticipation,
) -> ParticipantResponse:
    member = await members_repository.find_by_id(participation.member_id)
    return ParticipantResponse(
        id=participation.id,
        activity_id=participation.activity_id,
        member_id=participation.member_id,
        member_readable_id=participation.member_readable_id,
        member_name=member.full_name if member else None,
        member_email=member.email if member else None,
        role=participation.role,
        status=participation.status,
        source=participation.source,
        note=participation.note,
        invited_at=participation.invited_at,
        responded_at=participation.responded_at,
        confirmed_at=participation.confirmed_at,
        withdrawn_at=participation.withdrawn_at,
        email_sent_at=participation.email_sent_at,
        created_at=participation.created_at,
        updated_at=participation.updated_at,
    )
