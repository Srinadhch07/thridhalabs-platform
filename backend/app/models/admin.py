"""Admin account domain model and RBAC roles."""

from __future__ import annotations

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, ConfigDict, Field

from app.core.errors import AppError


class Role(str, Enum):
    OWNER = "owner"
    ADMIN = "admin"
    EDITOR = "editor"

    @property
    def rank(self) -> int:
        return ROLE_RANK[self]


# Higher rank = more privilege.
ROLE_RANK: dict[Role, int] = {
    Role.EDITOR: 1,
    Role.ADMIN: 2,
    Role.OWNER: 3,
}


def parse_role(value: str) -> Role:
    try:
        return Role(value)
    except ValueError as exc:
        raise AppError(400, "INVALID_ROLE", "Unknown role") from exc


def normalize_email(email: str) -> str:
    """Single normalisation rule used everywhere (storage, lookup, login)."""
    return email.strip().lower()


class Admin(BaseModel):
    """Internal admin representation. Never serialised to API responses
    directly — response schemas live in the auth module."""

    model_config = ConfigDict(extra="forbid")

    id: str
    email: str
    password_hash: str = Field(repr=False)
    role: Role
    is_active: bool = True
    token_version: int = 0
    created_at: datetime
    updated_at: datetime
    last_login_at: datetime | None = None

    @property
    def min_privilege_rank(self) -> int:
        return self.role.rank
