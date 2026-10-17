"""Reusable authentication / RBAC dependencies.

Future business routers protect endpoints like:

    @router.post("/things", dependencies=[Depends(require_role("owner"))])
"""

from __future__ import annotations

from typing import Awaitable, Callable

from fastapi import Depends, Request

from app.core.config import get_settings
from app.core.errors import AppError
from app.core.security import decode_admin_access_token
from app.models.admin import Admin, Role, ROLE_RANK
from app.modules.admins import repository

CSRF_HEADER_NAME = "X-CSRF-Token"


async def get_current_admin(request: Request) -> Admin:
    """Authenticate the request via the HttpOnly session cookie.

    Validates: cookie present → JWT signature/expiry → admin exists →
    token_version matches (revocation). Does NOT check `is_active`.
    """
    settings = get_settings()
    token = request.cookies.get(settings.COOKIE_NAME)
    if not token:
        raise AppError(401, "NOT_AUTHENTICATED", "Authentication required")

    claims = decode_admin_access_token(token)
    admin = await repository.find_by_id(claims["sub"])
    if admin is None:
        raise AppError(401, "SESSION_REVOKED", "Session is no longer valid")

    if admin.token_version != claims["tv"]:
        raise AppError(401, "SESSION_REVOKED", "Session is no longer valid")

    return admin


async def get_active_admin(
    admin: Admin = Depends(get_current_admin),
) -> Admin:
    """Like `get_current_admin` but requires the account to be active."""
    if not admin.is_active:
        raise AppError(403, "ACCOUNT_DISABLED", "This account is disabled")
    return admin


def require_role(minimum: Role | str) -> Callable[..., Awaitable[Admin]]:
    """Role gate using privilege ranks: owner(3) > admin(2) > editor(1).

    `require_role("owner")` therefore accepts only owners, while
    `require_role("editor")` accepts every role.
    """
    min_role = minimum if isinstance(minimum, Role) else Role(minimum)
    min_rank = ROLE_RANK[min_role]

    async def dependency(
        admin: Admin = Depends(get_active_admin),
    ) -> Admin:
        if admin.role.rank < min_rank:
            raise AppError(403, "INSUFFICIENT_ROLE", "Insufficient permissions")
        return admin

    dependency.__name__ = f"require_role_{min_role.value}"
    return dependency
