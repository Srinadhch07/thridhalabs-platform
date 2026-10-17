"""Admin provisioning: normalisation, hashing, uniqueness, model defaults."""

from __future__ import annotations

import pytest

from app.core.errors import AppError
from app.db.mongo import get_mongo
from app.models.admin import Role, normalize_email, parse_role


async def test_create_admin_normalizes_email(make_admin):
    admin = await make_admin("  Foo.Bar@Example.COM ")
    assert admin.email == "foo.bar@example.com"


async def test_create_admin_defaults(make_admin):
    admin = await make_admin("defaults@example.com")
    assert admin.role is Role.OWNER
    assert admin.is_active is True
    assert admin.token_version == 0
    assert admin.last_login_at is None
    assert admin.id
    assert len(admin.id) == 24


async def test_duplicate_email_is_rejected_regardless_of_case(make_admin):
    await make_admin("dupe@example.com")
    with pytest.raises(AppError) as exc:
        await make_admin("  DUPE@example.com  ")
    assert exc.value.status_code == 409
    assert exc.value.code == "EMAIL_TAKEN"


async def test_invalid_email_is_rejected(make_admin):
    with pytest.raises(AppError) as exc:
        await make_admin("not-an-email")
    assert exc.value.code == "INVALID_EMAIL"


async def test_password_is_stored_hashed_not_plaintext(make_admin):
    password = "CorrectHorse!Battery9"
    admin = await make_admin("stored@example.com", password=password)

    doc = await get_mongo().database["admins"].find_one({"email": "stored@example.com"})
    assert doc is not None
    stored = doc["password_hash"]
    assert stored != password
    assert password not in stored
    assert stored.startswith("$2")


async def test_admin_repr_does_not_leak_password_hash(make_admin):
    admin = await make_admin("repr@example.com")
    assert "password_hash" not in repr(admin)
    assert admin.password_hash not in repr(admin)


async def test_email_unique_index_exists(make_admin):
    await make_admin("index@example.com")
    indexes = await get_mongo().database["admins"].index_information()
    email_index = next(v for k, v in indexes.items() if k == "email_1")
    assert email_index["unique"] is True


def test_parse_role_accepts_valid_roles():
    assert parse_role("owner") is Role.OWNER
    assert parse_role("admin") is Role.ADMIN
    assert parse_role("editor") is Role.EDITOR


def test_parse_role_rejects_unknown_role():
    with pytest.raises(AppError) as exc:
        parse_role("superuser")
    assert exc.value.code == "INVALID_ROLE"
    assert exc.value.status_code == 400


def test_normalize_email_is_single_lowercase_rule():
    assert normalize_email("  Admin@EXAMPLE.com ") == "admin@example.com"


def test_role_ranks_are_ordered():
    assert Role.OWNER.rank > Role.ADMIN.rank > Role.EDITOR.rank
