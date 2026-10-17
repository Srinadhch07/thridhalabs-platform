"""Password hashing, verification and policy."""

from __future__ import annotations

import pytest

from app.core.errors import AppError
from app.core.security import (
    PASSWORD_MAX_LENGTH,
    PASSWORD_MIN_LENGTH,
    hash_password,
    validate_password_policy,
    verify_password,
)


def test_hash_is_salted_per_password():
    a = hash_password("CorrectHorse!9")
    b = hash_password("CorrectHorse!9")
    assert a != b, "bcrypt must use a fresh salt for every hash"


def test_hash_never_contains_plaintext_and_is_bcrypt():
    digest = hash_password("CorrectHorse!9")
    assert "CorrectHorse!9" not in digest
    assert digest.startswith("$2")


def test_verify_accepts_correct_password():
    digest = hash_password("CorrectHorse!9")
    assert verify_password("CorrectHorse!9", digest) is True


def test_verify_rejects_wrong_password():
    digest = hash_password("CorrectHorse!9")
    assert verify_password("CorrectHorse!8", digest) is False


def test_verify_rejects_malformed_hash():
    assert verify_password("whatever", "not-a-real-hash") is False


def test_policy_rejects_short_password():
    with pytest.raises(AppError) as exc:
        validate_password_policy("short")
    assert exc.value.code == "WEAK_PASSWORD"
    assert exc.value.status_code == 400


def test_policy_rejects_too_long_password():
    with pytest.raises(AppError) as exc:
        validate_password_policy("a" * (PASSWORD_MAX_LENGTH + 1))
    assert exc.value.code == "WEAK_PASSWORD"


def test_policy_accepts_valid_password():
    validate_password_policy("CorrectHorse!9")
    validate_password_policy("x" * PASSWORD_MIN_LENGTH)


def test_hash_password_enforces_policy():
    with pytest.raises(AppError) as exc:
        hash_password("tiny")
    assert exc.value.code == "WEAK_PASSWORD"
