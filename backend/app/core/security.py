"""Password hashing and JWT access-token utilities.

- Passwords: bcrypt (never stored or logged in plaintext).
- Tokens: HS256 JWTs signed with the configured `JWT_SECRET`, carrying
  `sub` (admin id), `role`, `tv` (token version), `iat` and `exp`.

This module is intentionally free of FastAPI imports so it can be reused by
the CLI, services and tests.
"""

from __future__ import annotations

import secrets
from datetime import datetime, timedelta, timezone
from functools import lru_cache
from typing import Any

import bcrypt
import jwt
from bson import ObjectId

from app.core.config import get_settings
from app.core.errors import AppError

ALGORITHM = "HS256"

# bcrypt silently truncates input at 72 bytes — reject longer passwords so the
# policy matches what is actually hashed.
PASSWORD_MIN_LENGTH = 10
PASSWORD_MAX_LENGTH = 72


# --------------------------------------------------------------------------
# Password policy + hashing
# --------------------------------------------------------------------------
def validate_password_policy(password: str) -> None:
    """Raise AppError(400) when a password does not meet the policy."""
    if len(password.strip()) < PASSWORD_MIN_LENGTH:
        raise AppError(
            400,
            "WEAK_PASSWORD",
            f"Password must be at least {PASSWORD_MIN_LENGTH} characters long",
        )
    if len(password) > PASSWORD_MAX_LENGTH:
        raise AppError(
            400,
            "WEAK_PASSWORD",
            f"Password must be at most {PASSWORD_MAX_LENGTH} characters long",
        )
    if not password.strip():
        raise AppError(400, "WEAK_PASSWORD", "Password must not be blank")


def hash_password(password: str) -> str:
    """Hash a password with bcrypt (salted, per-password)."""
    validate_password_policy(password)
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(password: str, password_hash: str) -> bool:
    """Constant-ish-time password check; malformed hashes simply fail."""
    try:
        return bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("utf-8"))
    except (ValueError, TypeError):
        return False


@lru_cache(maxsize=1)
def _dummy_password_hash() -> str:
    """Hash used to equalise timing when an email does not exist."""
    return bcrypt.hashpw(b"dummy-timing-equaliser", bcrypt.gensalt()).decode("utf-8")


def burn_password_time(password: str) -> None:
    """Perform a real bcrypt verification against a dummy hash."""
    verify_password(password, _dummy_password_hash())


# --------------------------------------------------------------------------
# CSRF tokens
# --------------------------------------------------------------------------
def generate_csrf_token() -> str:
    return secrets.token_urlsafe(32)


# --------------------------------------------------------------------------
# JWT access tokens
# --------------------------------------------------------------------------
def create_access_token(
    *,
    admin_id: str,
    role: str,
    token_version: int,
    expires_delta: timedelta | None = None,
) -> str:
    settings = get_settings()
    now = datetime.now(timezone.utc)
    expires = now + (expires_delta or timedelta(minutes=settings.JWT_ACCESS_MINUTES))
    payload: dict[str, Any] = {
        "sub": admin_id,
        "role": role,
        "tv": token_version,
        "iat": int(now.timestamp()),
        "exp": int(expires.timestamp()),
    }
    return jwt.encode(
        payload, settings.JWT_SECRET.get_secret_value(), algorithm=ALGORITHM
    )


def decode_access_token(token: str) -> dict[str, Any]:
    """Decode + validate a token, raising client-safe 401 AppErrors."""
    settings = get_settings()
    try:
        payload = jwt.decode(
            token,
            settings.JWT_SECRET.get_secret_value(),
            algorithms=[ALGORITHM],
            options={"require": ["sub", "exp", "iat"]},
        )
    except jwt.ExpiredSignatureError as exc:
        raise AppError(401, "TOKEN_EXPIRED", "Session has expired") from exc
    except jwt.InvalidTokenError as exc:
        raise AppError(401, "TOKEN_INVALID", "Invalid session token") from exc

    sub = payload.get("sub")
    role = payload.get("role")
    token_version = payload.get("tv")

    if (
        not isinstance(sub, str)
        or not ObjectId.is_valid(sub)
        or not isinstance(role, str)
        or not isinstance(token_version, int)
    ):
        raise AppError(401, "TOKEN_INVALID", "Invalid session token")

    return payload


# --------------------------------------------------------------------------
# Member session tokens
# --------------------------------------------------------------------------
def create_member_access_token(
    *,
    member_id: str,
    token_version: int,
    expires_delta: timedelta | None = None,
) -> str:
    """Issue a member JWT. The `typ=member` claim keeps member sessions
    distinguishable from admin sessions, which never carry it."""
    settings = get_settings()
    now = datetime.now(timezone.utc)
    expires = now + (expires_delta or timedelta(minutes=settings.JWT_ACCESS_MINUTES))
    payload: dict[str, Any] = {
        "sub": member_id,
        "role": "member",
        "tv": token_version,
        "typ": "member",
        "iat": int(now.timestamp()),
        "exp": int(expires.timestamp()),
    }
    return jwt.encode(
        payload, settings.JWT_SECRET.get_secret_value(), algorithm=ALGORITHM
    )


def decode_member_access_token(token: str) -> dict[str, Any]:
    """Decode a member token. Admin tokens (`typ` absent or != "member") are
    rejected — a member session can never be minted from an admin session and
    vice versa."""
    payload = decode_access_token(token)
    if payload.get("typ") != "member":
        raise AppError(401, "TOKEN_INVALID", "Invalid session token")
    return payload


def decode_admin_access_token(token: str) -> dict[str, Any]:
    """Decode an Admin token. Member tokens (``typ="member"``) are rejected so
    a member session can never be accepted as an Admin one, even if the member's
    identifier could otherwise resolve to an Admin document."""
    payload = decode_access_token(token)
    if payload.get("typ") == "member":
        raise AppError(401, "TOKEN_INVALID", "Invalid session token")
    return payload
