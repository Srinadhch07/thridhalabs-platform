from __future__ import annotations

import pytest
from pydantic import SecretStr, ValidationError

from app.core.config import Settings, get_settings


def test_settings_load_from_env_file():
    settings = get_settings()
    assert settings.API_PREFIX == "/api"
    assert settings.MONGO_DB_NAME
    assert settings.COOKIE_SAMESITE in ("lax", "strict", "none")
    assert settings.STORAGE_MODE in ("local", "s3")


def test_secrets_are_wrapped():
    settings = get_settings()
    assert isinstance(settings.JWT_SECRET, SecretStr)
    assert isinstance(settings.MONGO_URI, SecretStr)
    # repr/serialization must not leak the raw value
    assert "SecretStr" in repr(settings.JWT_SECRET)


def test_cors_never_contains_wildcard():
    origins = get_settings().cors_origin_list
    assert origins, "at least one CORS origin must be configured"
    assert "*" not in origins
    assert all(o.startswith(("http://", "https://")) for o in origins)


def _settings(**overrides) -> Settings:
    kwargs: dict = {
        "_env_file": None,
        "MONGO_URI": "mongodb://user:pass@localhost:27017/",
        "MONGO_DB_NAME": "test_db",
        "CORS_ORIGINS": "http://localhost:5173",
        "JWT_SECRET": "x" * 40,
        "COOKIE_NAME": "test_cookie",
        "CSRF_COOKIE_NAME": "test_csrf",
        "DEBUG": True,
    }
    kwargs.update(overrides)
    return Settings(**kwargs)


def test_invalid_storage_mode_is_rejected():
    with pytest.raises(ValidationError):
        _settings(STORAGE_MODE="ftp")


def test_wildcard_cors_is_rejected():
    with pytest.raises(ValidationError):
        _settings(CORS_ORIGINS="*")


def test_samesite_none_requires_secure():
    with pytest.raises(ValidationError):
        _settings(COOKIE_SAMESITE="none", COOKIE_SECURE=False)


def test_production_requires_secure_cookies():
    with pytest.raises(ValidationError):
        _settings(DEBUG=False, COOKIE_SECURE=False)


def test_api_prefix_must_be_absolute_path():
    with pytest.raises(ValidationError):
        _settings(API_PREFIX="api")
