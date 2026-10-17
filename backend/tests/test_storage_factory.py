"""Storage provider selection (factory) tests."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from app.core.config import ConfigurationError, Settings, get_settings
from app.storage import get_storage_provider
from app.storage.local import LocalStorageProvider


def test_get_storage_provider_returns_singleton():
    get_storage_provider.cache_clear()
    try:
        first = get_storage_provider()
        second = get_storage_provider()
        assert first is second
        assert isinstance(first, LocalStorageProvider)
        assert first.mode == "local"
    finally:
        get_storage_provider.cache_clear()


def test_local_provider_uses_configured_directory():
    settings = get_settings()
    assert settings.STORAGE_MODE == "local"
    root = get_storage_provider().root
    assert str(settings.STORAGE_LOCAL_DIR) in str(root)


def test_invalid_storage_mode_is_rejected_at_configuration():
    with pytest.raises(ValidationError):
        Settings(STORAGE_MODE="gcs")


def test_s3_mode_without_aws_configuration_fails_clearly(monkeypatch):
    monkeypatch.setenv("STORAGE_MODE", "s3")
    for key in ("AWS_REGION", "AWS_S3_BUCKET", "AWS_ACCESS_KEY_ID", "AWS_SECRET_ACCESS_KEY"):
        monkeypatch.setenv(key, "")
    get_settings.cache_clear()
    get_storage_provider.cache_clear()
    try:
        with pytest.raises(ConfigurationError):
            get_storage_provider()
    finally:
        get_storage_provider.cache_clear()
        get_settings.cache_clear()