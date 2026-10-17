"""Member authentication / authorization dependencies.

Member sessions use a dedicated HttpOnly cookie (`MEMBER_COOKIE_NAME`) plus a
dedicated double-submit CSRF cookie (`MEMBER_CSRF_COOKIE_NAME`), so an Admin and
a Lab Member can hold independent sessions in the same browser. The member JWT
additionally carries a `typ=member` claim: this module only accepts member
tokens, and the admin dependencies reject member tokens, so neither realm can
be authenticated with the other's token even if cookie names were ever shared.
"""

from __future__ import annotations

from fastapi import Depends, Request

from app.core.config import get_settings
from app.core.errors import AppError
from app.core.security import decode_member_access_token
from app.models.member import Member, MemberStatus
from app.modules.members import repository


async def get_current_member(request: Request) -> Member:
    """Authenticate via the session cookie and validate the member exists and
    its token_version is current. Does NOT check the member status."""
    settings = get_settings()
    token = request.cookies.get(settings.MEMBER_COOKIE_NAME)
    if not token:
        raise AppError(401, "NOT_AUTHENTICATED", "Authentication required")

    claims = decode_member_access_token(token)
    member = await repository.find_by_id(claims["sub"])
    if member is None:
        raise AppError(401, "SESSION_REVOKED", "Session is no longer valid")

    if member.token_version != claims["tv"]:
        raise AppError(401, "SESSION_REVOKED", "Session is no longer valid")

    return member


async def get_enabled_member(
    member: Member = Depends(get_current_member),
) -> Member:
    """Like `get_current_member` but rejects deactivated accounts. Members in
    `pending_setup` are allowed through so they can finish their profile."""
    if member.status == MemberStatus.INACTIVE:
        raise AppError(403, "ACCOUNT_DISABLED", "This account is disabled")
    return member