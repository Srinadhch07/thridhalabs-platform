"""Pydantic schemas for the AI settings API (Admin only).

Responses deliberately expose only *safe* metadata: whether a key is stored, a
masked hint, who/when it was set and the last connection-test result. The
encrypted token, its fingerprint and the plaintext key are never serialised.
"""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models.ai_settings import AiSettings


class AiSettingsUpdate(BaseModel):
    """Set/replace the Groq key and/or update model + enabled flag.

    A provided `api_key` replaces the stored one (setting a new key is an
    explicit act; removing it is a separate endpoint).
    """

    model_config = ConfigDict(extra="forbid")

    api_key: str | None = Field(default=None, max_length=400)
    model: str | None = Field(default=None, max_length=200)
    enabled: bool | None = None

    @field_validator("api_key")
    @classmethod
    def _api_key(cls, value: str | None) -> str | None:
        if value is None:
            return None
        value = value.strip()
        if not value:
            raise ValueError("API key must not be empty")
        if any(ch.isspace() for ch in value):
            raise ValueError("API key must not contain whitespace")
        if len(value) < 20 or len(value) > 400:
            raise ValueError("API key has an unexpected length")
        return value

    @field_validator("model")
    @classmethod
    def _model(cls, value: str | None) -> str | None:
        if value is None:
            return None
        value = value.strip()
        if not value:
            raise ValueError("Model must not be empty")
        return value


class AiConnectionTestRequest(BaseModel):
    """Optionally test a *proposed* key/model before saving it.

    When `api_key` is omitted the currently stored key is tested. A proposed key
    is used for the call only and is never persisted.
    """

    model_config = ConfigDict(extra="forbid")

    api_key: str | None = Field(default=None, max_length=400)
    model: str | None = Field(default=None, max_length=200)

    @field_validator("api_key")
    @classmethod
    def _api_key(cls, value: str | None) -> str | None:
        if value is None:
            return None
        value = value.strip()
        if not value or any(ch.isspace() for ch in value):
            raise ValueError("API key must not be empty or contain whitespace")
        return value

    @field_validator("model")
    @classmethod
    def _model(cls, value: str | None) -> str | None:
        if value is None:
            return None
        value = value.strip()
        return value or None


class AiSettingsResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    provider: str
    model: str
    enabled: bool
    configured: bool
    encryption_available: bool
    key_hint: str | None
    key_set_at: datetime | None
    key_set_by_name: str | None
    last_test_at: datetime | None
    last_test_ok: bool | None
    last_test_error: str | None
    updated_at: datetime


class AiConnectionTestResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    ok: bool
    model: str
    models_available: int | None = None
    model_available: bool | None = None
    latency_ms: int | None = None
    error_code: str | None = None
    error_message: str | None = None


def _masked_hint(settings: AiSettings) -> str | None:
    """A masked indicator — never the key. e.g. ``••••••••1234``."""
    if not settings.api_key_encrypted:
        return None
    hint = settings.key_hint or ""
    if hint:
        return f"\u2022\u2022\u2022\u2022\u2022\u2022\u2022\u2022{hint}"
    return "\u2022\u2022\u2022\u2022\u2022\u2022\u2022\u2022"


def admin_response(
    settings: AiSettings,
    *,
    encryption_available: bool,
    key_set_by_name: str | None,
) -> AiSettingsResponse:
    return AiSettingsResponse(
        provider=settings.provider,
        model=settings.model,
        enabled=settings.enabled,
        configured=settings.configured,
        encryption_available=encryption_available,
        key_hint=_masked_hint(settings),
        key_set_at=settings.key_set_at,
        key_set_by_name=key_set_by_name,
        last_test_at=settings.last_test_at,
        last_test_ok=settings.last_test_ok,
        last_test_error=settings.last_test_error,
        updated_at=settings.updated_at,
    )
