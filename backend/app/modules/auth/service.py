"""Authentication flows: login, logout, CSRF bootstrap."""

from __future__ import annotations

from fastapi import Request, Response

from app.core.config import get_settings
from app.core.cookies import (
    admin_cookies,
    clear_session_cookies,
    set_auth_cookie,
    set_csrf_cookie,
)
from app.core.errors import AppError
from app.core.logging import get_logger
from app.core.security import (
    burn_password_time,
    create_access_token,
    generate_csrf_token,
    verify_password,
)
from app.deps.auth import CSRF_HEADER_NAME  # noqa: F401  (re-exported for callers)
from app.models.admin import Admin, normalize_email
from app.modules.admins import repository
from app.modules.auth.schemas import LoginRequest
from app.services.rate_limit import login_rate_limiter

log = get_logger("auth")


def _client_key(request: Request) -> str:
    return request.client.host if request.client else "unknown"


def issue_csrf(response: Response) -> str:
    token = generate_csrf_token()
    settings = get_settings()
    set_csrf_cookie(response, token, settings, admin_cookies(settings))
    return token


async def perform_login(
    request: Request, response: Response, payload: LoginRequest
) -> None:
    settings = get_settings()
    client = _client_key(request)
    window_seconds = settings.LOGIN_RATE_LIMIT_WINDOW_MINUTES * 60

    limited, retry_after = login_rate_limiter.is_limited(
        client,
        max_attempts=settings.LOGIN_RATE_LIMIT_MAX,
        window_seconds=window_seconds,
    )
    if limited:
        log.warning("Login rate limit hit for %s", client)
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
    admin = await repository.find_by_email(email)

    if admin is None:
        # Equalise timing so unknown emails are not distinguishable.
        burn_password_time(payload.password)
        log.warning("Login failed (unknown account) from %s", client)
        raise _fail()

    if not verify_password(payload.password, admin.password_hash):
        log.warning("Login failed (bad password) for %s from %s", email, client)
        raise _fail()

    if not admin.is_active:
        log.warning("Login rejected — disabled account %s", email)
        raise AppError(403, "ACCOUNT_DISABLED", "This account is disabled")

    login_rate_limiter.reset(client)

    token = create_access_token(
        admin_id=admin.id,
        role=admin.role.value,
        token_version=admin.token_version,
    )
    csrf_token = generate_csrf_token()
    cookies = admin_cookies(settings)
    set_auth_cookie(response, token, settings, cookies)
    set_csrf_cookie(response, csrf_token, settings, cookies)
    await repository.touch_last_login(admin.id)
    log.info("Login succeeded for %s", email)


async def perform_logout(response: Response, admin: Admin) -> None:
    # Revocation: bump token_version so every outstanding JWT becomes invalid,
    # then clear the cookies (cookies alone would not revoke stolen tokens).
    await repository.bump_token_version(admin.id)
    settings = get_settings()
    clear_session_cookies(response, settings, admin_cookies(settings))
    log.info("Logout for %s — token_version bumped", admin.email)
