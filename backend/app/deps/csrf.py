"""Double-submit CSRF protection for cookie-authenticated requests.

- The JWT lives in an HttpOnly cookie (unreadable by scripts).
- The CSRF token lives in a readable cookie set by `GET /auth/csrf` (Admin) or
  `GET /member/csrf` (Member).
- Every state-changing request must echo the cookie value in the
  `X-CSRF-Token` header; an attacker on another origin can neither read
  the cookie nor set the header.

Each realm validates against its own CSRF cookie, so the two schemes never
share state. Attach it to mutations:

    @router.post("/x", dependencies=[Depends(require_csrf)])            # admin
    @router.post("/x", dependencies=[Depends(require_member_csrf)])     # member
"""

from __future__ import annotations

import secrets

from fastapi import Request

from app.core.config import get_settings
from app.core.errors import AppError
from app.deps.auth import CSRF_HEADER_NAME


async def _check_csrf(request: Request, cookie_name: str) -> None:
    cookie_token = request.cookies.get(cookie_name)
    header_token = request.headers.get(CSRF_HEADER_NAME)

    if not cookie_token or not header_token:
        raise AppError(403, "CSRF_MISSING", "CSRF token is required")

    if not secrets.compare_digest(cookie_token, header_token):
        raise AppError(403, "CSRF_INVALID", "CSRF token is invalid")


async def require_csrf(request: Request) -> None:
    """Admin double-submit check against the Admin CSRF cookie."""
    await _check_csrf(request, get_settings().CSRF_COOKIE_NAME)


async def require_member_csrf(request: Request) -> None:
    """Member double-submit check against the Member CSRF cookie."""
    await _check_csrf(request, get_settings().MEMBER_CSRF_COOKIE_NAME)
