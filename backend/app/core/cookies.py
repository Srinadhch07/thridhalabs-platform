"""Cookie helpers for cookie-based sessions (HttpOnly JWT + readable CSRF).

Admin and Lab Member sessions are fully independent: each realm has its own
authentication cookie and its own CSRF cookie, so signing in to one portal
never overwrites or clears the other's session in the same browser.
"""

from __future__ import annotations

from dataclasses import dataclass

from fastapi.responses import Response

from app.core.config import Settings


@dataclass(frozen=True)
class CookieNames:
    """The authentication + CSRF cookie names for a single realm."""

    session: str
    csrf: str


def admin_cookies(settings: Settings) -> CookieNames:
    return CookieNames(session=settings.COOKIE_NAME, csrf=settings.CSRF_COOKIE_NAME)


def member_cookies(settings: Settings) -> CookieNames:
    return CookieNames(
        session=settings.MEMBER_COOKIE_NAME, csrf=settings.MEMBER_CSRF_COOKIE_NAME
    )


def _shared_attrs(settings: Settings) -> dict:
    return {
        "path": "/",
        "domain": settings.COOKIE_DOMAIN or None,
        "secure": settings.COOKIE_SECURE,
        "samesite": settings.COOKIE_SAMESITE,
    }


def set_auth_cookie(
    response: Response, token: str, settings: Settings, cookies: CookieNames
) -> None:
    """HttpOnly JWT cookie — never readable from JavaScript."""
    response.set_cookie(
        key=cookies.session,
        value=token,
        max_age=settings.JWT_ACCESS_MINUTES * 60,
        httponly=True,
        **_shared_attrs(settings),
    )


def set_csrf_cookie(
    response: Response, token: str, settings: Settings, cookies: CookieNames
) -> None:
    """Readable double-submit CSRF cookie (deliberately NOT HttpOnly)."""
    response.set_cookie(
        key=cookies.csrf,
        value=token,
        max_age=settings.JWT_ACCESS_MINUTES * 60,
        httponly=False,
        **_shared_attrs(settings),
    )


def clear_session_cookies(
    response: Response, settings: Settings, cookies: CookieNames
) -> None:
    """Clear this realm's cookies (revocation happens via token_version).

    Deletion uses the same attributes as creation so the browser actually
    removes the intended cookies — only this realm's, never the other's.
    """
    attrs = _shared_attrs(settings)
    response.delete_cookie(key=cookies.session, **attrs)
    response.delete_cookie(key=cookies.csrf, **attrs)
