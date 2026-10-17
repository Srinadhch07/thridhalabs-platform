"""Member account business logic: provisioning, onboarding, login, profile
management and the admin lifecycle (deactivate / reactivate / resend / delete).

Members are provisioned by admins only. Session handling is deliberately
mirrored from the existing admin auth flow (HttpOnly cookie + double-submit
CSRF + token_version revocation) so there is exactly one session model in the
codebase.
"""

from __future__ import annotations

import hashlib
import re
import secrets
from datetime import datetime, timedelta, timezone
from urllib.parse import quote

from fastapi import Request, Response
from pymongo.errors import DuplicateKeyError

from app.core.config import get_settings
from app.core.cookies import (
    clear_session_cookies,
    member_cookies,
    set_auth_cookie,
    set_csrf_cookie,
)
from app.core.errors import AppError
from app.core.logging import get_logger
from app.core.security import (
    burn_password_time,
    create_member_access_token,
    generate_csrf_token,
    hash_password,
    validate_password_policy,
    verify_password,
)
from app.models.admin import Admin, normalize_email
from app.models.member import (
    Member,
    MemberOnboarding,
    MemberProfile,
    MemberStatus,
)
from app.modules.careers import repository as careers_repository
from app.modules.members import repository
from app.modules.members.schemas import (
    MemberCreateRequest,
    MemberLoginRequest,
    MemberPasswordChangeRequest,
    MemberProfileUpdate,
    MemberSetupRequest,
    MemberUpdateRequest,
)
from app.services.email import EmailDeliveryError, send_email
from app.services.rate_limit import login_rate_limiter, onboarding_rate_limiter

# Imported lazily in functions that touch storage to keep module import cheap,
# but the media service is the ONLY component that talks to providers.

log = get_logger("members")

ONBOARDING_TTL_HOURS = 24
ALLOCATION_ATTEMPTS = 5


# --------------------------------------------------------------------------
# Helpers
# --------------------------------------------------------------------------
def _client_key(request: Request) -> str:
    return request.client.host if request.client else "unknown"


def issue_member_csrf(response: Response) -> str:
    """Issue a member-scoped CSRF cookie (the member portal's bootstrap).

    Uses a dedicated cookie so it never clobbers the Admin CSRF cookie.
    """
    token = generate_csrf_token()
    settings = get_settings()
    set_csrf_cookie(response, token, settings, member_cookies(settings))
    return token


def _hash_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def _as_utc(value: datetime | None) -> datetime | None:
    """MongoDB returns naive datetimes; treat stored values as UTC so they can
    be compared against timezone-aware `now`."""
    if value is None:
        return None
    return value if value.tzinfo is not None else value.replace(tzinfo=timezone.utc)


def _new_onboarding() -> tuple[str, MemberOnboarding]:
    token = secrets.token_urlsafe(48)
    now = datetime.now(timezone.utc)
    onboarding = MemberOnboarding(
        token_hash=_hash_token(token),
        expires_at=now + timedelta(hours=ONBOARDING_TTL_HOURS),
        sent_at=None,
        completed_at=None,
    )
    return token, onboarding


def resolve_setup_base_url() -> str:
    """Build the trusted base URL for setup links.

    Uses `FRONTEND_URL` when configured, otherwise the first configured CORS
    origin (the frontend's own origin). An arbitrary `Host` header is NEVER
    consulted.
    """
    settings = get_settings()
    if settings.FRONTEND_URL:
        return settings.FRONTEND_URL.rstrip("/")
    origins = settings.cors_origin_list
    if origins:
        return origins[0].rstrip("/")
    raise AppError(
        500,
        "SETUP_URL_NOT_CONFIGURED",
        "The frontend URL is not configured; a setup link cannot be built",
    )


def _setup_url(token: str) -> str:
    return f"{resolve_setup_base_url()}/member/setup?token={quote(token)}"


def _desired_status(member: Member) -> MemberStatus:
    """Derive the stored status from onboarding + profile completion.

    Inactive is sticky here — only an explicit reactivation changes it.
    """
    if member.status == MemberStatus.INACTIVE:
        return MemberStatus.INACTIVE
    if member.onboarding.completed_at is not None and member.profile_complete:
        return MemberStatus.ACTIVE
    return MemberStatus.PENDING_SETUP


def _desired_status_for(member: Member, profile: MemberProfile) -> MemberStatus:
    if member.status == MemberStatus.INACTIVE:
        return MemberStatus.INACTIVE
    if (
        member.onboarding.completed_at is not None
        and profile.is_complete(full_name=member.full_name)
    ):
        return MemberStatus.ACTIVE
    return MemberStatus.PENDING_SETUP


async def _validate_opportunity(opportunity_id: str) -> None:
    opportunity = await careers_repository.find_opportunity_by_id(opportunity_id)
    if opportunity is None:
        raise AppError(
            400, "INVALID_OPPORTUNITY", "The linked opportunity does not exist"
        )


def _is_email_duplicate(exc: DuplicateKeyError) -> bool:
    details = getattr(exc, "details", None) or {}
    pattern = details.get("keyPattern") or {}
    return "email" in pattern


async def _send_onboarding_email(member: Member, token: str) -> bool:
    """Best-effort delivery. Returns True on success; a failure is logged and
    surfaced to the admin as `onboarding_sent=false` (retry via resend)."""
    greeting = member.full_name or "there"
    text = (
        f"Hi {greeting},\n\n"
        "An account has been created for you at Thridha Labs.\n"
        f"Your member ID: {member.member_id}\n\n"
        "Set your password and complete your profile using this single-use "
        f"link (valid for {ONBOARDING_TTL_HOURS} hours):\n"
        f"{_setup_url(token)}\n\n"
        "If you were not expecting this email you can safely ignore it."
    )
    try:
        await send_email(
            to=member.email,
            subject="Set up your Thridha Labs member account",
            text=text,
        )
        return True
    except EmailDeliveryError as exc:
        log.error(
            "Onboarding email delivery failed for member %s: %s",
            member.member_id,
            exc,
        )
        return False


async def _delete_owned_picture(member: Member, media_id: str) -> None:
    """Delete a profile-picture media document, but only when this member is
    its creator (never a shared/deduplicated asset created by someone else)."""
    from app.modules.media import service as media_service

    try:
        media = await media_service.get_media(media_id)
    except AppError:
        return
    if media.created_by != member.id:
        return
    try:
        await media_service.delete_media(media_id)
    except AppError as exc:
        log.warning(
            "Could not delete profile picture %s for member %s: %s",
            media_id,
            member.member_id,
            exc,
        )


async def _get_or_404(record_id: str) -> Member:
    member = await repository.find_by_id(record_id)
    if member is None:
        raise AppError(404, "MEMBER_NOT_FOUND", "Member was not found")
    return member


# --------------------------------------------------------------------------
# Admin: provisioning + lifecycle
# --------------------------------------------------------------------------
async def create_member(payload: MemberCreateRequest, admin: Admin) -> Member:
    email = normalize_email(str(payload.email))
    if await repository.email_exists(email):
        raise AppError(409, "EMAIL_TAKEN", "A member with this email already exists")
    if payload.joined_opportunity_id:
        await _validate_opportunity(payload.joined_opportunity_id)

    token, onboarding = _new_onboarding()
    member: Member | None = None
    last_error: DuplicateKeyError | None = None
    for _ in range(ALLOCATION_ATTEMPTS):
        member_id = await repository.allocate_member_id()
        try:
            member = await repository.insert_member(
                member_id=member_id,
                email=email,
                full_name=payload.full_name,
                role_label=payload.role_label,
                joined_opportunity_id=payload.joined_opportunity_id,
                internal_note=payload.internal_note,
                created_by=admin.id,
                onboarding=onboarding,
            )
            last_error = None
            break
        except DuplicateKeyError as exc:
            last_error = exc
            if _is_email_duplicate(exc) or await repository.email_exists(email):
                raise AppError(
                    409, "EMAIL_TAKEN", "A member with this email already exists"
                ) from exc
            # Otherwise it was a (vanishingly rare) member-id collision — retry.

    if member is None:
        log.error("Member id allocation failed after %d attempts", ALLOCATION_ATTEMPTS)
        raise AppError(
            500, "MEMBER_CREATE_FAILED", "The member account could not be created"
        ) from last_error

    if await _send_onboarding_email(member, token):
        sent_onboarding = onboarding.model_copy(
            update={"sent_at": datetime.now(timezone.utc)}
        )
        member = await repository.set_onboarding(member.id, sent_onboarding) or member

    log.info(
        "Member created member_id=%s email=%s by admin=%s onboarding_sent=%s",
        member.member_id,
        member.email,
        admin.id,
        member.onboarding.sent_at is not None,
    )
    return member


async def list_members(
    *,
    page: int,
    page_size: int,
    status: str | None,
    search: str | None,
    sort: list[tuple],
) -> tuple[list[Member], int]:
    query: dict = {}
    if status:
        query["status"] = status
    if search:
        pattern = re.escape(search.strip())
        query["$or"] = [
            {"email": {"$regex": pattern, "$options": "i"}},
            {"full_name": {"$regex": pattern, "$options": "i"}},
            {"member_id": {"$regex": pattern, "$options": "i"}},
            {"role_label": {"$regex": pattern, "$options": "i"}},
        ]
    return await repository.list_members(
        page=page, page_size=page_size, query=query, sort=sort
    )


async def get_member(record_id: str) -> Member:
    return await _get_or_404(record_id)


async def update_member(record_id: str, payload: MemberUpdateRequest) -> Member:
    member = await _get_or_404(record_id)
    provided = payload.model_fields_set
    fields: dict = {}

    if "email" in provided:
        if payload.email is None:
            raise AppError(422, "INVALID_EMAIL", "A valid email address is required")
        fields["email"] = normalize_email(str(payload.email))
    if "full_name" in provided:
        fields["full_name"] = payload.full_name
    if "role_label" in provided:
        fields["role_label"] = payload.role_label
    if "joined_opportunity_id" in provided:
        if payload.joined_opportunity_id:
            await _validate_opportunity(payload.joined_opportunity_id)
        fields["joined_opportunity_id"] = payload.joined_opportunity_id
    if "internal_note" in provided:
        fields["internal_note"] = payload.internal_note

    if not fields:
        return member

    if "email" in fields and await repository.email_exists(
        fields["email"], exclude_id=record_id
    ):
        raise AppError(409, "EMAIL_TAKEN", "A member with this email already exists")

    try:
        updated = await repository.update_admin_fields(record_id, fields)
    except DuplicateKeyError as exc:
        raise AppError(
            409, "EMAIL_TAKEN", "A member with this email already exists"
        ) from exc
    if updated is None:
        raise AppError(404, "MEMBER_NOT_FOUND", "Member was not found")

    if "full_name" in fields:
        desired = _desired_status(updated)
        if desired != updated.status:
            updated = await repository.set_status(record_id, desired) or updated
    return updated


async def deactivate_member(record_id: str) -> Member:
    member = await _get_or_404(record_id)
    if member.status == MemberStatus.INACTIVE:
        return member
    await repository.bump_token_version(record_id)  # revoke live sessions
    onboarding = member.onboarding.model_copy(update={"token_hash": None})
    await repository.set_onboarding(record_id, onboarding)  # kill any setup link
    updated = await repository.set_status(record_id, MemberStatus.INACTIVE)
    log.info("Member deactivated member_id=%s", member.member_id)
    return updated or member


async def reactivate_member(record_id: str) -> Member:
    member = await _get_or_404(record_id)
    if member.status != MemberStatus.INACTIVE:
        return member

    if member.onboarding.completed_at is not None:
        target = MemberStatus.ACTIVE if member.profile_complete else MemberStatus.PENDING_SETUP
        return await repository.set_status(record_id, target) or member

    # Never completed onboarding: issue a fresh single-use link.
    token, onboarding = _new_onboarding()
    await repository.set_onboarding(record_id, onboarding)
    member = await repository.set_status(record_id, MemberStatus.PENDING_SETUP) or member
    if await _send_onboarding_email(member, token):
        sent = onboarding.model_copy(update={"sent_at": datetime.now(timezone.utc)})
        member = await repository.set_onboarding(record_id, sent) or member
    log.info("Member reactivated (fresh setup link) member_id=%s", member.member_id)
    return member


async def resend_onboarding(record_id: str) -> Member:
    member = await _get_or_404(record_id)
    if member.status == MemberStatus.INACTIVE:
        raise AppError(403, "ACCOUNT_DISABLED", "This account is disabled")
    if member.onboarding.completed_at is not None:
        raise AppError(
            409,
            "ONBOARDING_ALREADY_COMPLETE",
            "This member has already completed setup",
        )
    token, onboarding = _new_onboarding()
    await repository.set_onboarding(record_id, onboarding)  # invalidates the old link
    if await _send_onboarding_email(member, token):
        sent = onboarding.model_copy(update={"sent_at": datetime.now(timezone.utc)})
        member = await repository.set_onboarding(record_id, sent) or member
    else:
        member = await repository.find_by_id(record_id) or member
    log.info("Onboarding resent member_id=%s", member.member_id)
    return member


async def delete_member(record_id: str) -> None:
    member = await _get_or_404(record_id)
    if member.profile.picture_media_id:
        await _delete_owned_picture(member, member.profile.picture_media_id)
    await repository.delete_by_id(record_id)
    log.info("Member deleted member_id=%s email=%s", member.member_id, member.email)


# --------------------------------------------------------------------------
# Member self-service: onboarding + session
# --------------------------------------------------------------------------
async def perform_setup(request: Request, payload: MemberSetupRequest) -> Member:
    settings = get_settings()
    client = _client_key(request)
    window_seconds = settings.LOGIN_RATE_LIMIT_WINDOW_MINUTES * 60

    limited, retry_after = onboarding_rate_limiter.is_limited(
        client,
        max_attempts=settings.LOGIN_RATE_LIMIT_MAX,
        window_seconds=window_seconds,
    )
    if limited:
        raise AppError(
            429,
            "RATE_LIMITED",
            "Too many attempts. Please try again later.",
            headers={"Retry-After": str(retry_after)},
        )

    def _reject() -> AppError:
        onboarding_rate_limiter.record_failure(
            client,
            max_attempts=settings.LOGIN_RATE_LIMIT_MAX,
            window_seconds=window_seconds,
        )
        return AppError(
            400,
            "INVALID_ONBOARDING_TOKEN",
            "This setup link is invalid or has already been used",
        )

    member = await repository.find_by_onboarding_token_hash(_hash_token(payload.token))
    if member is None or member.onboarding.completed_at is not None:
        raise _reject()
    if member.status == MemberStatus.INACTIVE:
        raise AppError(403, "ACCOUNT_DISABLED", "This account is disabled")

    now = datetime.now(timezone.utc)
    expires_at = _as_utc(member.onboarding.expires_at)
    if expires_at is None or now > expires_at:
        raise AppError(
            400,
            "ONBOARDING_TOKEN_EXPIRED",
            "This setup link has expired. Please ask an admin to resend it.",
        )

    validate_password_policy(payload.password)
    password_hash = hash_password(payload.password)
    status = MemberStatus.ACTIVE if member.profile_complete else MemberStatus.PENDING_SETUP

    updated = await repository.set_password_and_complete_onboarding(
        member.id,
        password_hash=password_hash,
        completed_at=now,
        status=status,
    )
    if updated is None:
        raise AppError(404, "MEMBER_NOT_FOUND", "Member was not found")
    onboarding_rate_limiter.reset(client)
    log.info("Member onboarding completed member_id=%s", updated.member_id)
    return updated


async def perform_login(
    request: Request, response: Response, payload: MemberLoginRequest
) -> Member:
    settings = get_settings()
    client = _client_key(request)
    window_seconds = settings.LOGIN_RATE_LIMIT_WINDOW_MINUTES * 60

    limited, retry_after = login_rate_limiter.is_limited(
        client,
        max_attempts=settings.LOGIN_RATE_LIMIT_MAX,
        window_seconds=window_seconds,
    )
    if limited:
        log.warning("Member login rate limit hit for %s", client)
        raise AppError(
            429,
            "RATE_LIMITED",
            "Too many login attempts. Please try again later.",
            headers={"Retry-After": str(retry_after)},
        )

    def _fail() -> AppError:
        login_rate_limiter.record_failure(
            client,
            max_attempts=settings.LOGIN_RATE_LIMIT_MAX,
            window_seconds=window_seconds,
        )
        return AppError(401, "INVALID_CREDENTIALS", "Invalid email or password")

    email = normalize_email(str(payload.email))
    member = await repository.find_by_email(email)

    if member is None or member.password_hash is None:
        burn_password_time(payload.password)
        log.warning("Member login failed (unknown/incomplete account) from %s", client)
        raise _fail()

    if not verify_password(payload.password, member.password_hash):
        log.warning("Member login failed (bad password) for %s from %s", email, client)
        raise _fail()

    if member.status == MemberStatus.INACTIVE:
        log.warning("Member login rejected — disabled account %s", email)
        raise AppError(403, "ACCOUNT_DISABLED", "This account is disabled")

    login_rate_limiter.reset(client)

    token = create_member_access_token(
        member_id=member.id, token_version=member.token_version
    )
    csrf_token = generate_csrf_token()
    cookies = member_cookies(settings)
    set_auth_cookie(response, token, settings, cookies)
    set_csrf_cookie(response, csrf_token, settings, cookies)
    await repository.touch_last_login(member.id)
    log.info("Member login succeeded for %s", email)
    return member


async def perform_logout(response: Response, member: Member) -> None:
    await repository.bump_token_version(member.id)
    settings = get_settings()
    clear_session_cookies(response, settings, member_cookies(settings))
    log.info("Member logout member_id=%s — token_version bumped", member.member_id)


async def change_password(
    member: Member, payload: MemberPasswordChangeRequest
) -> None:
    if member.password_hash is None:
        raise AppError(
            400, "PASSWORD_NOT_SET", "Set your password before changing it"
        )
    if not verify_password(payload.current_password, member.password_hash):
        raise AppError(401, "INVALID_PASSWORD", "Current password is incorrect")
    if payload.current_password == payload.new_password:
        raise AppError(
            400, "PASSWORD_UNCHANGED", "Choose a password different from the current one"
        )
    validate_password_policy(payload.new_password)
    new_hash = hash_password(payload.new_password)
    await repository.set_password_hash(member.id, new_hash)
    log.info("Member password changed member_id=%s", member.member_id)


# --------------------------------------------------------------------------
# Member self-service: profile + picture
# --------------------------------------------------------------------------
async def update_profile(member: Member, payload: MemberProfileUpdate) -> Member:
    now = datetime.now(timezone.utc)
    profile = MemberProfile(
        display_name=payload.display_name,
        bio=payload.bio,
        skills=payload.skills,
        interests=payload.interests,
        github_url=payload.github_url,
        linkedin_url=payload.linkedin_url,
        portfolio_url=payload.portfolio_url,
        location=payload.location,
        timezone=payload.timezone,
        picture_media_id=member.profile.picture_media_id,
        profile_visibility=(
            payload.profile_visibility
            if payload.profile_visibility is not None
            else member.profile.profile_visibility
        ),
        completed_at=member.profile.completed_at,
    )
    if profile.is_complete(full_name=member.full_name) and profile.completed_at is None:
        profile.completed_at = now

    status = _desired_status_for(member, profile)
    updated = await repository.set_profile(member.id, profile=profile, status=status)
    if updated is None:
        raise AppError(404, "MEMBER_NOT_FOUND", "Member was not found")
    return updated


async def upload_profile_picture(
    member: Member, *, data: bytes, original_name: str | None
):
    """Upload an avatar through the shared media pipeline and associate it.

    Ownership is enforced: a member may only associate media they created. If
    the upload de-duplicates onto an asset owned by someone else, the upload is
    rejected rather than silently sharing that asset.
    """
    from app.modules.media import service as media_service

    result = await media_service.upload_media(
        data=data, original_name=original_name, created_by=member.id
    )
    media = result.media
    if media.created_by != member.id:
        raise AppError(
            409,
            "MEDIA_NOT_OWNED",
            "That image is already registered to another account; upload a different image",
        )

    previous = member.profile.picture_media_id
    if previous and previous != media.id:
        await _delete_owned_picture(member, previous)

    profile = member.profile.model_copy(update={"picture_media_id": media.id})
    await repository.set_profile(
        member.id, profile=profile, status=_desired_status_for(member, profile)
    )
    log.info("Member picture set member_id=%s media_id=%s", member.member_id, media.id)
    return media


async def clear_profile_picture(member: Member) -> Member:
    previous = member.profile.picture_media_id
    if not previous:
        return member
    await _delete_owned_picture(member, previous)
    profile = member.profile.model_copy(update={"picture_media_id": None})
    updated = await repository.set_profile(
        member.id, profile=profile, status=_desired_status_for(member, profile)
    )
    return updated or member


# --------------------------------------------------------------------------
# Member media library (member-owned assets for the work showcase)
# --------------------------------------------------------------------------
async def upload_member_media(
    member: Member, *, data: bytes, original_name: str | None
):
    """Upload an image into the member's own media library.

    Uses the shared media pipeline (size/dimension/type validation, dedup,
    variant processing). De-duplication onto a record owned by someone else is
    rejected — a member can only ever reference their own uploads.
    """
    from app.modules.media import service as media_service

    result = await media_service.upload_media(
        data=data, original_name=original_name, created_by=member.id
    )
    media = result.media
    if media.created_by != member.id:
        raise AppError(
            409,
            "MEDIA_NOT_OWNED",
            "That image is already registered to another account; upload a different image",
        )
    log.info(
        "Member media uploaded member_id=%s media_id=%s created=%s",
        member.member_id,
        media.id,
        result.created,
    )
    return result


async def list_member_media(
    member: Member, *, page: int, page_size: int, sort: str
):
    from app.modules.media import service as media_service

    return await media_service.list_member_media(
        creator_id=member.id, page=page, page_size=page_size, sort=sort
    )


# --------------------------------------------------------------------------
# Public profile (readable member id; active + public profile only)
# --------------------------------------------------------------------------
async def get_public_member(member_readable_id: str) -> Member:
    from app.models.member import ProfileVisibility

    member = await repository.find_by_readable_id(member_readable_id)
    if member is None or member.status != MemberStatus.ACTIVE:
        raise AppError(404, "MEMBER_NOT_FOUND", "Member profile is not public")
    if member.profile.profile_visibility != ProfileVisibility.PUBLIC:
        raise AppError(404, "MEMBER_NOT_FOUND", "Member profile is not public")
    return member