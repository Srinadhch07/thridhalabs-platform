"""Application settings.

Reads the repository-root `.env` file using the EXISTING variable names as a
fixed contract. Variable names are never renamed. Secret values are wrapped in
`SecretStr` so they can never be printed, logged or serialized by accident.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Literal
from urllib.parse import urlparse

from pydantic import Field, SecretStr, ValidationError, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# backend/app/core/config.py -> parents: [core, app, backend, repo root]
REPO_ROOT = Path(__file__).resolve().parents[3]
ENV_FILE = REPO_ROOT / ".env"

LOG_LEVELS = ("DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL")
STORAGE_MODES = ("local", "s3")


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=ENV_FILE,
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )

    # --- Application ---
    APP_NAME: str = "ThridhaLabs"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False
    LOG_LEVEL: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = "WARNING"
    API_PREFIX: str = "/api"

    # --- Database ---
    MONGO_URI: SecretStr
    MONGO_DB_NAME: str
    MONGO_TIMEOUT_MS: int = Field(default=3000, ge=100, le=60_000)

    # --- CORS ---
    CORS_ORIGINS: str

    # --- Authentication / sessions (used from Phase 2) ---
    JWT_SECRET: SecretStr
    JWT_ACCESS_MINUTES: int = Field(default=30, ge=5, le=1440)
    COOKIE_NAME: str
    CSRF_COOKIE_NAME: str
    # Member portal sessions use dedicated cookies so an Admin and a Lab Member
    # can stay signed in simultaneously in the same browser. Safe defaults keep
    # the root `.env` unchanged; the names must not collide with the Admin ones.
    MEMBER_COOKIE_NAME: str = "thridha_labs_member"
    MEMBER_CSRF_COOKIE_NAME: str = "thridha_labs_member_csrf"
    COOKIE_DOMAIN: str | None = None
    COOKIE_SECURE: bool = True
    COOKIE_SAMESITE: Literal["lax", "strict", "none"] = "none"

    # --- Rate limiting (used from Phase 2) ---
    LOGIN_RATE_LIMIT_MAX: int = Field(default=5, ge=1, le=1000)
    LOGIN_RATE_LIMIT_WINDOW_MINUTES: int = Field(default=15, ge=1, le=1440)

    # --- Storage (local + S3 providers, selected by STORAGE_MODE) ---
    STORAGE_MODE: Literal["local", "s3"] = "local"
    STORAGE_LOCAL_DIR: str = "storage-local"
    PRODUCT_IMAGE_MAX_BYTES: int = Field(default=5_242_880, ge=1024)
    # Activity PDF briefs use their own limit (separate from images).
    ACTIVITY_BRIEF_MAX_BYTES: int = Field(default=20_971_520, ge=1024)
    AWS_ACCESS_KEY_ID: SecretStr | None = None
    AWS_SECRET_ACCESS_KEY: SecretStr | None = None
    AWS_REGION: str | None = None
    AWS_S3_BUCKET: str | None = None

    # --- Media image pipeline (Phase 3) ---
    # Decompression-bomb guard: reject images whose pixel count exceeds this.
    MEDIA_MAX_IMAGE_PIXELS: int = Field(default=40_000_000, ge=1_000_000, le=1_000_000_000)
    # Responsive variant max-dimensions (never upscale smaller sources).
    MEDIA_THUMB_SIZE: int = Field(default=256, ge=16, le=4096)
    MEDIA_MD_SIZE: int = Field(default=1024, ge=64, le=8192)
    MEDIA_LG_SIZE: int = Field(default=1920, ge=256, le=16384)

    # --- Email (used from Phase 4) ---
    SMTP_HOST: str | None = None
    SMTP_PORT: int = Field(default=587, ge=1, le=65535)
    SMTP_USERNAME: SecretStr | None = None
    SMTP_PASSWORD: SecretStr | None = None
    SMTP_FROM_EMAIL: str | None = None
    # Never touch SMTP (log-only "transport"). Tests and local verification
    # force this so real mail is never sent from a development environment.
    EMAIL_MOCK: bool = False

    # --- Frontend ---
    FRONTEND_URL: str = ""

    # --- Certificates ---
    # Canonical public origin used to build the certificate verification URL that
    # is encoded into the QR code. Falls back to FRONTEND_URL when unset. Never a
    # localhost address: a QR printed on a PDF must resolve for third parties.
    CERTIFICATE_VERIFY_BASE_URL: str = ""

    # --- AI summarization (Groq) ---
    # Dedicated, stable encryption key for the *dynamic* Groq API key stored via
    # the Admin UI. It is deliberately SEPARATE from JWT_SECRET: a signing key
    # must never be reused for encryption. When unset the AI settings surface
    # still loads, but storing/changing a key is refused (NO plaintext fallback).
    # Provide a high-entropy, at-least-32-character value (e.g. `python -m
    # app.cli.generate_ai_key`). Wrap in SecretStr so it can never be printed.
    AI_SETTINGS_ENCRYPTION_KEY: SecretStr | None = None
    # Groq is OpenAI-compatible; the base URL is configurable so a proxy can be
    # used in restricted environments. The API key itself is never an env var —
    # it is entered by an Admin and stored encrypted.
    GROQ_API_BASE_URL: str = "https://api.groq.com/openai/v1"

    # ---------------------------------------------------------------
    # Derived values
    # ---------------------------------------------------------------
    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",") if origin.strip()]

    @property
    def is_production(self) -> bool:
        return not self.DEBUG

    @property
    def verification_base_url(self) -> str | None:
        """Normalized origin for certificate verification links, or None."""
        base = (self.CERTIFICATE_VERIFY_BASE_URL or self.FRONTEND_URL or "").strip()
        base = base.rstrip("/")
        return base or None

    @property
    def ai_encryption_configured(self) -> bool:
        """True when a dedicated AI settings encryption key is available."""
        if self.AI_SETTINGS_ENCRYPTION_KEY is None:
            return False
        return bool(self.AI_SETTINGS_ENCRYPTION_KEY.get_secret_value().strip())

    # ---------------------------------------------------------------
    # Validation
    # ---------------------------------------------------------------
    @field_validator("API_PREFIX")
    @classmethod
    def _validate_api_prefix(cls, value: str) -> str:
        if not value.startswith("/"):
            raise ValueError("API_PREFIX must start with '/'")
        if value != "/" and value.endswith("/"):
            raise ValueError("API_PREFIX must not end with '/'")
        return value

    @field_validator("STORAGE_LOCAL_DIR")
    @classmethod
    def _validate_storage_dir(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("STORAGE_LOCAL_DIR must not be empty")
        return value

    @field_validator("COOKIE_DOMAIN", "FRONTEND_URL", "CERTIFICATE_VERIFY_BASE_URL")
    @classmethod
    def _strip_blank(cls, value: str | None) -> str | None:
        if value is None:
            return None
        value = value.strip()
        return value or None

    @field_validator("AI_SETTINGS_ENCRYPTION_KEY")
    @classmethod
    def _validate_ai_encryption_key(
        cls, value: SecretStr | None
    ) -> SecretStr | None:
        if value is None:
            return None
        raw = value.get_secret_value().strip()
        if not raw:
            return None
        if len(raw) < 32:
            raise ValueError(
                "AI_SETTINGS_ENCRYPTION_KEY must be at least 32 characters"
            )
        return SecretStr(raw)

    @field_validator("GROQ_API_BASE_URL")
    @classmethod
    def _validate_groq_base_url(cls, value: str) -> str:
        value = value.strip().rstrip("/")
        if not value.startswith(("http://", "https://")):
            raise ValueError("GROQ_API_BASE_URL must be an http(s) URL")
        return value

    @model_validator(mode="after")
    def _validate_cross_field(self) -> "Settings":
        errors: list[str] = []

        # CORS: never a wildcard, always well-formed origins.
        origins = self.cors_origin_list
        if not origins:
            errors.append("CORS_ORIGINS must contain at least one origin")
        if any(origin == "*" for origin in origins):
            errors.append("CORS_ORIGINS must never contain the wildcard '*'")
        for origin in origins:
            parsed = urlparse(origin)
            if parsed.scheme not in ("http", "https") or not parsed.netloc:
                errors.append(f"CORS origin must be an http(s) URL: {origin}")
            elif parsed.username or parsed.password:
                errors.append("CORS origin must not embed credentials")
            elif parsed.path not in ("", "/"):
                errors.append(f"CORS origin must not contain a path: {origin}")

        # Cookie policy invariants (browsers reject other combinations).
        if self.COOKIE_SAMESITE == "none" and not self.COOKIE_SECURE:
            errors.append("COOKIE_SAMESITE=none requires COOKIE_SECURE=true")

        # Admin and member sessions must never share a cookie name — doing so
        # would reintroduce the cross-portal session overwrite bug.
        admin_cookies = {self.COOKIE_NAME, self.CSRF_COOKIE_NAME}
        member_cookies = {self.MEMBER_COOKIE_NAME, self.MEMBER_CSRF_COOKIE_NAME}
        if "" in admin_cookies or "" in member_cookies:
            errors.append("cookie names must not be empty")
        overlap = admin_cookies & member_cookies
        if overlap:
            errors.append(
                "MEMBER_COOKIE_NAME / MEMBER_CSRF_COOKIE_NAME must differ from the "
                "Admin cookie names"
            )

        # Frontend URL, when set, must be an absolute http(s) URL.
        if self.FRONTEND_URL and not self.FRONTEND_URL.startswith(("http://", "https://")):
            errors.append("FRONTEND_URL must be an http(s) URL")

        # Certificate verify base URL, when set, must be an absolute http(s) URL.
        if self.CERTIFICATE_VERIFY_BASE_URL and not self.CERTIFICATE_VERIFY_BASE_URL.startswith(
            ("http://", "https://")
        ):
            errors.append("CERTIFICATE_VERIFY_BASE_URL must be an http(s) URL")

        # MongoDB URI shape (validated in memory only — never printed).
        uri = self.MONGO_URI.get_secret_value()
        if not uri.startswith(("mongodb://", "mongodb+srv://")):
            errors.append("MONGO_URI must start with mongodb:// or mongodb+srv://")

        # Production-sensitive fail-fast checks.
        if self.is_production:
            if not self.COOKIE_SECURE:
                errors.append("Production requires COOKIE_SECURE=true (HTTPS)")
            if len(self.JWT_SECRET.get_secret_value()) < 32:
                errors.append("Production requires a JWT_SECRET of at least 32 characters")

        if errors:
            raise ValueError("; ".join(errors))

        return self


class ConfigurationError(RuntimeError):
    """Raised when the environment configuration is invalid."""


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Load and cache application settings (fails fast on invalid config)."""
    try:
        return Settings()
    except ValidationError as exc:  # pragma: no cover - exercised manually
        # Pydantic's error output only names fields/inputs; secret VALUES are
        # never included because they are SecretStr.
        raise ConfigurationError(
            f"Invalid environment configuration:\n{exc}"
        ) from exc
