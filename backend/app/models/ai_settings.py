"""Groq AI settings domain model (dynamic API key management).

There is exactly one AI settings document per environment (unique `singleton`).
The Groq API key is stored **only** as an authenticated-encryption token (see
`app.core.crypto`). The plaintext key is never persisted, returned by an API,
logged or written to any file the application manages.

Alongside the ciphertext a short non-reversible fingerprint (change detection)
and a 4-character tail (`key_hint`, for a masked indicator) are kept. Neither is
the key, and the fingerprint/hint are never returned to any client.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict

SINGLETON_KEY = "ai_settings"
PROVIDER = "groq"
# A current, generally-available Groq chat model. Admins can change it at any
# time via the settings UI (the value is verified against Groq's model list when
# testing the connection).
DEFAULT_MODEL = "openai/gpt-oss-120b"


class AiSettings(BaseModel):
    """Internal AI settings representation (maps 1:1 with the persisted doc)."""

    model_config = ConfigDict(extra="forbid")

    id: str
    singleton: str = SINGLETON_KEY
    provider: str = PROVIDER
    model: str = DEFAULT_MODEL
    enabled: bool = True
    # Ciphertext token (see app.core.crypto) — never plaintext, never returned.
    api_key_encrypted: str | None = None
    key_fingerprint: str | None = None
    key_hint: str | None = None
    key_set_at: datetime | None = None
    key_set_by: str | None = None
    last_test_at: datetime | None = None
    last_test_ok: bool | None = None
    last_test_error: str | None = None
    created_at: datetime
    updated_at: datetime

    @property
    def configured(self) -> bool:
        """A key is stored (encrypted)."""
        return self.api_key_encrypted is not None


def default_ai_settings_doc() -> dict[str, Any]:
    """The empty/default AI settings document (no secret material)."""
    return {
        "singleton": SINGLETON_KEY,
        "provider": PROVIDER,
        "model": DEFAULT_MODEL,
        "enabled": True,
        "api_key_encrypted": None,
        "key_fingerprint": None,
        "key_hint": None,
        "key_set_at": None,
        "key_set_by": None,
        "last_test_at": None,
        "last_test_ok": None,
        "last_test_error": None,
    }
