"""Branding singleton domain model and defaults.

Mirrors the settings singleton: one document per environment, lazily created on
first write, defaults centralized. Media references store media record IDs only
— the media system owns the actual files.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator
from pydantic_core import PydanticCustomError

SINGLETON_KEY = "branding"

_HEX_RE = __import__("re").compile(r"^#[0-9a-fA-F]{6}$")

# Optional theme preset identifiers offered by the Branding designer. The
# field is nullable and purely presentational metadata — existing saved custom
# palettes (or documents without the field) are always accepted.
BRANDING_THEME_PRESETS = (
    "arctic_white",
    "ivory_indigo",
    "pearl_emerald",
    "midnight_slate",
    "obsidian_violet",
    "graphite_amber",
)


class BrandColors(BaseModel):
    model_config = ConfigDict(extra="forbid")

    primary: str = "#4f46e5"
    secondary: str = "#0ea5e9"
    accent: str = "#f59e0b"
    background: str = "#ffffff"
    text: str = "#0f172a"

    @field_validator("primary", "secondary", "accent", "background", "text")
    @classmethod
    def _hex_color(cls, value: str) -> str:
        value = value.strip().lower()
        if not _HEX_RE.fullmatch(value):
            raise PydanticCustomError(
                "hex_color", "Value must be a #rrggbb hex color"
            )
        return value


class BrandingMedia(BaseModel):
    """Media record references — IDs only, no file payloads or paths."""

    model_config = ConfigDict(extra="forbid")

    logo: str | None = None
    logo_dark: str | None = None
    logo_light: str | None = None
    favicon: str | None = None
    og_image: str | None = None


class Branding(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    singleton: str = SINGLETON_KEY
    colors: BrandColors = Field(default_factory=BrandColors)
    mode: Literal["light", "dark"] = "light"
    theme_preset: str | None = None
    media: BrandingMedia = Field(default_factory=BrandingMedia)
    created_at: datetime
    updated_at: datetime

    @field_validator("theme_preset")
    @classmethod
    def _theme_preset(cls, value: str | None) -> str | None:
        if value is not None and value not in BRANDING_THEME_PRESETS:
            raise PydanticCustomError(
                "theme_preset", "Unknown branding theme preset"
            )
        return value


def default_branding_doc() -> dict[str, Any]:
    """Default (neutral) branding; not tied to real Thridha Labs assets."""
    return {
        "singleton": SINGLETON_KEY,
        "colors": BrandColors().model_dump(),
        "mode": "light",
        "theme_preset": None,
        "media": {},
    }