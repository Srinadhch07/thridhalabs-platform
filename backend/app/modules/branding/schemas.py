"""Pydantic schemas for the branding API.

Media fields carry media record IDs only — the media system later resolves and
serves the actual files. The public response mirrors the admin response minus
nothing sensitive (only presentation data is modelled); note that branding is
purely presentational, so a single safe response shape is shared.
"""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, field_validator
from pydantic_core import PydanticCustomError

from app.models.branding import BRANDING_THEME_PRESETS, Branding

_HEX_RE = __import__("re").compile(r"^#[0-9a-fA-F]{6}$")


def _hex(value: str | None) -> str | None:
    if value is None:
        return None
    value = value.strip().lower()
    if not _HEX_RE.fullmatch(value):
        raise PydanticCustomError(
            "hex_color", "Value must be a #rrggbb hex color"
        )
    return value


class BrandingColorsUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    primary: str | None = None
    secondary: str | None = None
    accent: str | None = None
    background: str | None = None
    text: str | None = None

    @field_validator("primary", "secondary", "accent", "background", "text")
    @classmethod
    def _hex_color(cls, value: str | None) -> str | None:
        return _hex(value)


class BrandingMediaUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    logo: str | None = None
    logo_dark: str | None = None
    logo_light: str | None = None
    favicon: str | None = None
    og_image: str | None = None


class BrandingUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    colors: BrandingColorsUpdate | None = None
    mode: Literal["light", "dark"] | None = None
    media: BrandingMediaUpdate | None = None
    # Nullable optional metadata. Setting a value selects a preset; sending an
    # explicit null (or omitting during a replace) marks the palette custom.
    theme_preset: str | None = None

    @field_validator("theme_preset")
    @classmethod
    def _theme_preset(cls, value: str | None) -> str | None:
        if value is not None and value not in BRANDING_THEME_PRESETS:
            raise PydanticCustomError(
                "theme_preset", "Unknown branding theme preset"
            )
        return value


# --------------------------------------------------------------------------
# Responses
# --------------------------------------------------------------------------
class ColorsResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    primary: str
    secondary: str
    accent: str
    background: str
    text: str


class BrandingMediaResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    logo: str | None
    logo_dark: str | None
    logo_light: str | None
    favicon: str | None
    og_image: str | None


class BrandingAdminResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    colors: ColorsResponse
    mode: Literal["light", "dark"]
    theme_preset: str | None
    media: BrandingMediaResponse
    created_at: datetime
    updated_at: datetime


class BrandingPublicResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    colors: ColorsResponse
    mode: Literal["light", "dark"]
    media: BrandingMediaResponse


def admin_response(branding: Branding) -> BrandingAdminResponse:
    return BrandingAdminResponse(
        id=branding.id,
        colors=ColorsResponse(**branding.colors.model_dump()),
        mode=branding.mode,
        theme_preset=branding.theme_preset,
        media=BrandingMediaResponse(**branding.media.model_dump()),
        created_at=branding.created_at,
        updated_at=branding.updated_at,
    )


def public_response(branding: Branding) -> BrandingPublicResponse:
    return BrandingPublicResponse(
        colors=ColorsResponse(**branding.colors.model_dump()),
        mode=branding.mode,
        media=BrandingMediaResponse(**branding.media.model_dump()),
    )