"""Admin account provisioning (used by the CLI and by tests)."""

from __future__ import annotations

from pymongo.errors import DuplicateKeyError

from app.core.errors import AppError
from app.core.logging import get_logger
from app.core.security import hash_password, validate_password_policy
from app.models.admin import Admin, Role, normalize_email
from app.modules.admins import repository

log = get_logger("admins")


async def create_admin(
    email: str,
    password: str,
    role: Role | str = Role.OWNER,
    is_active: bool = True,
) -> Admin:
    """Validate, normalise, hash and persist a new admin account.

    Raises:
        AppError 400 — invalid email / weak password / invalid role
        AppError 409 — an account with this email already exists
    """
    normalized = normalize_email(email)
    if not normalized or "@" not in normalized:
        raise AppError(400, "INVALID_EMAIL", "A valid email address is required")

    if isinstance(role, str):
        role = Role(role)

    validate_password_policy(password)
    password_hash = hash_password(password)

    try:
        admin = await repository.insert_admin(
            email=normalized,
            password_hash=password_hash,
            role=role.value,
            is_active=is_active,
        )
    except DuplicateKeyError as exc:
        raise AppError(
            409, "EMAIL_TAKEN", "An account with this email already exists"
        ) from exc

    log.info("Created admin account %s (role=%s)", normalized, role.value)
    return admin
