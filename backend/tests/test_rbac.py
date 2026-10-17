"""RBAC dependency tests: require_role / get_active_admin privilege gates."""

from __future__ import annotations

from datetime import datetime, timezone

import pytest
from bson import ObjectId

from app.core.errors import AppError
from app.deps.auth import get_active_admin, require_role
from app.models.admin import Admin, Role


def _admin(role: Role, *, is_active: bool = True) -> Admin:
    now = datetime.now(timezone.utc)
    return Admin(
        id=str(ObjectId()),
        email=f"{role.value}-{ObjectId()}@rbac.test",
        password_hash="$2b$12$notusedinthesetests000000000000000000000000000",
        role=role,
        is_active=is_active,
        token_version=0,
        created_at=now,
        updated_at=now,
    )


async def test_owner_gate_accepts_owner():
    owner = _admin(Role.OWNER)
    result = await require_role("owner")(admin=owner)
    assert result is owner


async def test_owner_gate_rejects_admin():
    with pytest.raises(AppError) as exc:
        await require_role("owner")(admin=_admin(Role.ADMIN))
    assert exc.value.status_code == 403
    assert exc.value.code == "INSUFFICIENT_ROLE"


async def test_owner_gate_rejects_editor():
    with pytest.raises(AppError) as exc:
        await require_role(Role.OWNER)(admin=_admin(Role.EDITOR))
    assert exc.value.status_code == 403
    assert exc.value.code == "INSUFFICIENT_ROLE"


async def test_admin_gate_accepts_owner_and_admin():
    owner = _admin(Role.OWNER)
    admin = _admin(Role.ADMIN)
    assert await require_role("admin")(admin=owner) is owner
    assert await require_role("admin")(admin=admin) is admin


async def test_admin_gate_rejects_editor():
    with pytest.raises(AppError):
        await require_role("admin")(admin=_admin(Role.EDITOR))


async def test_editor_gate_accepts_every_role():
    for role in Role:
        member = _admin(role)
        assert await require_role("editor")(admin=member) is member


async def test_inactive_admin_is_rejected_even_with_role():
    with pytest.raises(AppError) as exc:
        await get_active_admin(admin=_admin(Role.OWNER, is_active=False))
    assert exc.value.status_code == 403
    assert exc.value.code == "ACCOUNT_DISABLED"


def test_unknown_minimum_role_fails_fast():
    with pytest.raises(ValueError):
        require_role("superuser")
