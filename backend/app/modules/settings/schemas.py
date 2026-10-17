"""Pydantic schemas for the settings API.

Public responses expose only presentation data (general/contact/social/footer
and SEO defaults). Analytics identifiers and the maintenance flag are
admin-only internal configuration and are never serialized publicly.
"""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.core.validators import optional_email, optional_http_url, optional_text
from app.models.settings import SiteSettings


class GeneralUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    site_name: str | None = Field(default=None, max_length=120)
    tagline: str | None = Field(default=None, max_length=300)
    description: str | None = Field(default=None, max_length=2000)


class ContactUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    contact_email: str | None = None
    contact_phone: str | None = Field(default=None, max_length=60)
    whatsapp: str | None = Field(default=None, max_length=60)
    address: str | None = Field(default=None, max_length=500)

    @field_validator("contact_email")
    @classmethod
    def _email(cls, value: str | None) -> str | None:
        return optional_email(value)

    @field_validator("contact_phone", "whatsapp", "address")
    @classmethod
    def _trim(cls, value: str | None) -> str | None:
        return optional_text(value, 500)


class SocialUpdate(BaseModel):
    """`urls` may add/change keys (http(s) URLs) or clear them with ""."""

    model_config = ConfigDict(extra="forbid")

    urls: dict[str, str] = Field(default_factory=dict, max_length=20)

    @field_validator("urls")
    @classmethod
    def _urls(cls, urls: dict[str, str]) -> dict[str, str]:
        clean: dict[str, str] = {}
        for key, value in urls.items():
            key = key.strip().lower()
            if not key or len(key) > 40 or not key.replace("_", "").replace("-", "").isalnum():
                raise ValueError(f"Unsafe social key: {key!r}")
            value = (value or "").strip()
            if value and not value.startswith(("http://", "https://")):
                raise ValueError("Social URLs must be http(s) URLs")
            clean[key] = value
        return clean


class FooterUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    copyright_text: str | None = Field(default=None, max_length=500)


class SeoUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    seo_title: str | None = Field(default=None, max_length=150)
    seo_description: str | None = Field(default=None, max_length=500)
    seo_keywords: list[str] | None = Field(default=None, max_length=50)

    @field_validator("seo_keywords")
    @classmethod
    def _keywords(cls, values: list[str] | None) -> list[str] | None:
        if values is None:
            return None
        for value in values:
            if len(value) > 80:
                raise ValueError("Each keyword must be at most 80 characters")
        return values


class AnalyticsUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    google_verification: str | None = Field(default=None, max_length=200)
    google_analytics: str | None = Field(default=None, max_length=100)


class SettingsUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    general: GeneralUpdate | None = None
    contact: ContactUpdate | None = None
    social: SocialUpdate | None = None
    footer: FooterUpdate | None = None
    seo: SeoUpdate | None = None
    analytics: AnalyticsUpdate | None = None
    maintenance_mode: bool | None = None


# --------------------------------------------------------------------------
# Responses
# --------------------------------------------------------------------------
class GeneralResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    site_name: str
    tagline: str
    description: str


class ContactResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    contact_email: str | None
    contact_phone: str | None
    whatsapp: str | None
    address: str | None


class SocialResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    urls: dict[str, str]


class FooterResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    copyright_text: str


class SeoResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    seo_title: str
    seo_description: str
    seo_keywords: list[str]


class AnalyticsResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    google_verification: str | None
    google_analytics: str | None


class SettingsAdminResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    general: GeneralResponse
    contact: ContactResponse
    social: SocialResponse
    footer: FooterResponse
    seo: SeoResponse
    analytics: AnalyticsResponse
    maintenance_mode: bool
    created_at: datetime
    updated_at: datetime


class SettingsPublicResponse(BaseModel):
    """Safe public subset - analytics stay admin-only.

    `maintenance_mode` is intentionally public: it is a plain boolean system
    state (visible anyway once the maintenance page shows) and the public
    frontend gate cannot work without it.
    """

    model_config = ConfigDict(extra="forbid")

    general: GeneralResponse
    contact: ContactResponse
    social: SocialResponse
    footer: FooterResponse
    seo: SeoResponse
    maintenance_mode: bool


def _social_urls(settings: SiteSettings) -> dict[str, str]:
    return dict(settings.social.urls)


def admin_response(settings: SiteSettings) -> SettingsAdminResponse:
    return SettingsAdminResponse(
        id=settings.id,
        general=GeneralResponse(**settings.general.model_dump()),
        contact=ContactResponse(**settings.contact.model_dump()),
        social=SocialResponse(urls=_social_urls(settings)),
        footer=FooterResponse(**settings.footer.model_dump()),
        seo=SeoResponse(**settings.seo.model_dump()),
        analytics=AnalyticsResponse(**settings.analytics.model_dump()),
        maintenance_mode=settings.maintenance_mode,
        created_at=settings.created_at,
        updated_at=settings.updated_at,
    )


def public_response(settings: SiteSettings) -> SettingsPublicResponse:
    return SettingsPublicResponse(
        general=GeneralResponse(**settings.general.model_dump()),
        contact=ContactResponse(**settings.contact.model_dump()),
        social=SocialResponse(urls=_social_urls(settings)),
        footer=FooterResponse(**settings.footer.model_dump()),
        seo=SeoResponse(**settings.seo.model_dump()),
        maintenance_mode=settings.maintenance_mode,
    )