"""Authenticated encryption for secrets stored at rest (AI settings).

The dynamic Groq API key is the only secret this module protects. It is
encrypted with **AES-256-GCM** (an AEAD cipher: confidentiality *and* integrity)
using a dedicated 32-byte key derived — via HKDF-SHA256 — from the
``AI_SETTINGS_ENCRYPTION_KEY`` environment value.

Design rules (deliberate, security-relevant):

- The encryption key is strictly separate from ``JWT_SECRET``. A JWT signing key
  must never be reused for encryption (different algorithms, different threat
  models, independent rotation).
- Ciphertexts are versioned and self-describing so the scheme can evolve:
  ``v1:<base64url(nonce[12] || ciphertext+tag)>``. The nonce is 96 random bits
  per encryption (never reused); the GCM tag authenticates the ciphertext, so a
  tampered token fails decryption rather than decoding to garbage.
- When no encryption key is configured, encryption is *unavailable*. Callers must
  refuse to persist a secret — there is intentionally **no plaintext fallback**.
"""

from __future__ import annotations

import base64
import hashlib
import os

from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.hkdf import HKDF

from app.core.config import get_settings
from app.core.errors import AppError

_VERSION = "v1"
_NONCE_BYTES = 12
_KEY_BYTES = 32
_HKDF_INFO = b"thridha-labs:ai-settings:v1"


class EncryptionUnavailableError(RuntimeError):
    """Raised when no ``AI_SETTINGS_ENCRYPTION_KEY`` is configured.

    Callers must translate this into a controlled error and must never fall back
    to storing a secret in plaintext.
    """


def is_encryption_configured() -> bool:
    """Whether a usable encryption key is present in the configuration."""
    return get_settings().ai_encryption_configured


def _root_key() -> bytes | None:
    settings = get_settings()
    if settings.AI_SETTINGS_ENCRYPTION_KEY is None:
        return None
    raw = settings.AI_SETTINGS_ENCRYPTION_KEY.get_secret_value().strip()
    return raw.encode("utf-8") if raw else None


def _derive_key() -> bytes:
    root = _root_key()
    if root is None:
        raise EncryptionUnavailableError(
            "AI settings encryption key is not configured"
        )
    hkdf = HKDF(
        algorithm=hashes.SHA256(),
        length=_KEY_BYTES,
        salt=None,
        info=_HKDF_INFO,
    )
    return hkdf.derive(root)


def encrypt_secret(plaintext: str) -> str:
    """Encrypt a secret. Raises `EncryptionUnavailableError` when unconfigured."""
    key = _derive_key()
    nonce = os.urandom(_NONCE_BYTES)
    ciphertext = AESGCM(key).encrypt(nonce, plaintext.encode("utf-8"), None)
    payload = base64.urlsafe_b64encode(nonce + ciphertext).decode("ascii")
    return f"{_VERSION}:{payload}"


def decrypt_secret(token: str) -> str:
    """Decrypt a token produced by `encrypt_secret`.

    Raises a client-safe `AppError` (500) on a tampered/corrupt token and
    `EncryptionUnavailableError` when no key is configured.
    """
    try:
        version, _, payload = token.partition(":")
        if version != _VERSION or not payload:
            raise ValueError("unsupported token")
        blob = base64.urlsafe_b64decode(payload.encode("ascii"))
        if len(blob) <= _NONCE_BYTES:
            raise ValueError("truncated token")
        nonce, ciphertext = blob[:_NONCE_BYTES], blob[_NONCE_BYTES:]
        key = _derive_key()
        return AESGCM(key).decrypt(nonce, ciphertext, None).decode("utf-8")
    except EncryptionUnavailableError:
        raise
    except Exception as exc:  # noqa: BLE001 - normalize every failure
        # Never surface cryptographic detail to a client.
        raise AppError(
            500,
            "AI_KEY_UNREADABLE",
            "The stored AI key could not be read. Please re-enter it.",
        ) from exc


def fingerprint(secret: str) -> str:
    """A short, non-reversible digest used only for change detection.

    This is NOT a password-style KDF (the key is high-entropy), but it too must
    never be returned to a client or logged — it is stored alongside the
    ciphertext purely so a later key can be recognised as different.
    """
    return hashlib.sha256(secret.encode("utf-8")).hexdigest()[:16]
