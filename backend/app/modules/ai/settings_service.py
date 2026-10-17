"""AI settings service — dynamic Groq key management.

Rules enforced here (never only in the UI):

- The Groq key is stored **encrypted** using the dedicated key from
  `app.core.crypto`. If no encryption key is configured, storing/changing a key
  is refused with a clear error — a secret is never written in plaintext.
- The stored key (plaintext or ciphertext) is never returned to any API caller.
- A proposed key can be *tested* without being saved; the connection test never
  mutates stored state except the health record of the currently stored key.
"""

from __future__ import annotations

from datetime import datetime, timezone

from app.core import crypto
from app.core.crypto import EncryptionUnavailableError
from app.core.errors import AppError
from app.models.admin import Admin
from app.models.ai_settings import AiSettings, default_ai_settings_doc
from app.modules.admins import repository as admins_repository
from app.modules.ai import groq, settings_repository
from app.modules.ai.settings_schemas import (
    AiConnectionTestRequest,
    AiConnectionTestResponse,
    AiSettingsResponse,
    AiSettingsUpdate,
    admin_response,
)

_HINT_TAIL = 4


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _hint(api_key: str) -> str:
    return api_key[-_HINT_TAIL:]


async def get_settings_doc() -> AiSettings:
    """Return the stored settings, or an in-memory default when absent.

    A GET never persists anything (mirrors the site-settings singleton)."""
    existing = await settings_repository.get()
    if existing is not None:
        return existing
    now = _now()
    return AiSettings(id="default", created_at=now, updated_at=now, **default_ai_settings_doc())


async def get_decrypted_key() -> str | None:
    """Decrypt the stored key for a server-side call, or None when unset."""
    settings = await settings_repository.get()
    if settings is None or settings.api_key_encrypted is None:
        return None
    return crypto.decrypt_secret(settings.api_key_encrypted)


async def _persist(existing: AiSettings | None, body: dict) -> AiSettings:
    now = _now()
    created_at = existing.created_at if existing is not None else now
    merged = {
        **(existing.model_dump(exclude={"id", "singleton"}) if existing else default_ai_settings_doc()),
        **body,
        "created_at": created_at,
        "updated_at": now,
    }
    return await settings_repository.upsert(merged)


async def update_settings(admin: Admin, payload: AiSettingsUpdate) -> AiSettings:
    """Replace the key (when provided) and/or update model + enabled flag."""
    existing = await settings_repository.get()
    body: dict = {}

    if payload.api_key is not None:
        if not crypto.is_encryption_configured():
            raise AppError(
                409,
                "AI_ENCRYPTION_UNAVAILABLE",
                "AI settings encryption is not configured. Set "
                "AI_SETTINGS_ENCRYPTION_KEY on the server before storing a key.",
            )
        try:
            encrypted = crypto.encrypt_secret(payload.api_key)
        except EncryptionUnavailableError as exc:  # pragma: no cover - guarded above
            raise AppError(
                409,
                "AI_ENCRYPTION_UNAVAILABLE",
                "AI settings encryption is not configured.",
            ) from exc
        body.update(
            {
                "api_key_encrypted": encrypted,
                "key_fingerprint": crypto.fingerprint(payload.api_key),
                "key_hint": _hint(payload.api_key),
                "key_set_at": _now(),
                "key_set_by": admin.id,
                # A newly replaced key has not been tested yet.
                "last_test_at": None,
                "last_test_ok": None,
                "last_test_error": None,
            }
        )

    if payload.model is not None:
        body["model"] = payload.model
    if payload.enabled is not None:
        body["enabled"] = payload.enabled

    if not body:
        # Nothing to change — return current state (still a no-op write).
        return await settings_repository.get() or await get_settings_doc()

    return await _persist(existing, body)


async def remove_key() -> AiSettings:
    """Remove the stored key. Idempotent."""
    existing = await settings_repository.get()
    body = {
        "api_key_encrypted": None,
        "key_fingerprint": None,
        "key_hint": None,
        "key_set_at": None,
        "key_set_by": None,
        "last_test_at": None,
        "last_test_ok": None,
        "last_test_error": None,
    }
    return await _persist(existing, body)


async def status_response(admin: Admin) -> AiSettingsResponse:
    settings = await get_settings_doc()
    key_set_by_name: str | None = None
    if settings.key_set_by:
        setter = await admins_repository.find_by_id(settings.key_set_by)
        if setter is not None:
            key_set_by_name = setter.email
    return admin_response(
        settings,
        encryption_available=crypto.is_encryption_configured(),
        key_set_by_name=key_set_by_name,
    )


async def test_connection(
    admin: Admin, payload: AiConnectionTestRequest
) -> AiConnectionTestResponse:
    """Test a proposed key (unsaved) or the stored key against Groq."""
    stored = await settings_repository.get()

    proposed = payload.api_key is not None
    if proposed:
        api_key = payload.api_key
    else:
        api_key = await get_decrypted_key()
        if api_key is None:
            raise AppError(
                409,
                "AI_NOT_CONFIGURED",
                "No Groq API key is configured yet.",
            )

    model = (payload.model or (stored.model if stored else None) or "").strip()

    try:
        result = await groq.test_connection(api_key, model or None)
    except groq.GroqError as exc:
        # Record health only for the *stored* key (a proposed key's failure is
        # not the stored key's fault).
        if not proposed:
            await _persist(
                stored,
                {
                    "last_test_at": _now(),
                    "last_test_ok": False,
                    "last_test_error": exc.message,
                },
            )
        return AiConnectionTestResponse(
            ok=False,
            model=model,
            error_code=exc.code,
            error_message=exc.message,
        )

    if not proposed:
        await _persist(
            stored,
            {
                "last_test_at": _now(),
                "last_test_ok": True,
                "last_test_error": None,
            },
        )

    return AiConnectionTestResponse(
        ok=True,
        model=model,
        models_available=result.get("models_available"),
        model_available=result.get("model_available"),
        latency_ms=result.get("latency_ms"),
    )
