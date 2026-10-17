"""Site-wide settings domain model and singleton defaults.

There is exactly one settings document per environment (singleton key: the
unique `singleton` field). A GET never persists anything; PUT/PATCH creates the
document on first write. Defaults are centralized here so both the empty state
and a partial update behave predictably.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.core.validators import optional_email

SINGLETON_KEY = "settings"


class GeneralSettings(BaseModel):
    model_config = ConfigDict(extra="forbid")

    site_name: str = "Thridha Labs"
    tagline: str = ""
    description: str = ""


class ContactSettings(BaseModel):
    model_config = ConfigDict(extra="forbid")

    contact_email: str | None = None
    contact_phone: str | None = None
    whatsapp: str | None = None
    address: str | None = None

    @field_validator("contact_email")
    @classmethod
    def _optional_email(cls, value: str | None) -> str | None:
        return optional_email(value)


class SocialSettings(BaseModel):
    """Extensible set of social profile URLs keyed by network name.

    No fixed list is enforced: any safe key may be stored (linkedin, github,
    instagram, x/twitter, youtube, ...). Empty strings clear a key.
    """

    model_config = ConfigDict(extra="forbid")

    urls: dict[str, str] = Field(default_factory=dict, max_length=20)

    @field_validator("urls")
    @classmethod
    def _validate_urls(cls, urls: dict[str, str]) -> dict[str, str]:
        clean: dict[str, str] = {}
        for key, value in urls.items():
            key = key.strip().lower()
            if not key or len(key) > 40 or not key.replace("_", "").replace("-", "").isalnum():
                raise ValueError(f"Unsafe social key: {key!r}")
            value = (value or "").strip()
            if not value:
                continue  # empty value clears the key
            if not value.startswith(("http://", "https://")):
                raise ValueError("Social URLs must be http(s) URLs")
            clean[key] = value
        return clean


class FooterSettings(BaseModel):
    model_config = ConfigDict(extra="forbid")

    copyright_text: str = ""


class SeoSettings(BaseModel):
    model_config = ConfigDict(extra="forbid")

    seo_title: str = ""
    seo_description: str = ""
    seo_keywords: list[str] = Field(default_factory=list, max_length=50)

    @field_validator("seo_keywords")
    @classmethod
    def _trim_keywords(cls, values: list[str]) -> list[str]:
        cleaned = [v.strip()[:80] for v in values if v.strip()]
        return list(dict.fromkeys(cleaned))[:50]


class AnalyticsSettings(BaseModel):
    """Verification/analytics identifiers. Admin-only configuration — never
    exposed through public APIs. Credentials (team tokens, API secrets) are
    deliberately not modelled here at all."""

    model_config = ConfigDict(extra="forbid")

    google_verification: str | None = None
    google_analytics: str | None = None


class SiteSettings(BaseModel):
    """Internal settings representation (maps 1:1 with the persisted doc)."""

    model_config = ConfigDict(extra="forbid")

    id: str
    singleton: str = SINGLETON_KEY
    general: GeneralSettings = Field(default_factory=GeneralSettings)
    contact: ContactSettings = Field(default_factory=ContactSettings)
    social: SocialSettings = Field(default_factory=SocialSettings)
    footer: FooterSettings = Field(default_factory=FooterSettings)
    seo: SeoSettings = Field(default_factory=SeoSettings)
    analytics: AnalyticsSettings = Field(default_factory=AnalyticsSettings)
    maintenance_mode: bool = False
    created_at: datetime
    updated_at: datetime


def default_settings_doc() -> dict[str, Any]:
    """The empty/default settings document (no fake business content)."""
    return {
        "singleton": SINGLETON_KEY,
        "general": GeneralSettings().model_dump(),
        "contact": ContactSettings().model_dump(),
        "social": {"urls": {}},
        "footer": FooterSettings().model_dump(),
        "seo": SeoSettings().model_dump(),
        "analytics": AnalyticsSettings().model_dump(),
        "maintenance_mode": False,
    }