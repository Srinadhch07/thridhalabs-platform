"""Small shared field validators used across content schemas.

Kept separate from the per-module schemas so URL/colour rules stay identical for
clients, projects, testimonials and branding.
"""

from __future__ import annotations

import re

_EMAIL_RE = re.compile(r"^[A-Z0-9._%+\-]+@[A-Z0-9\-]+\.[A-Z]{2,}$", re.IGNORECASE)


def optional_http_url(value: str | None) -> str | None:
    """Normalize an optional URL field: strip, reject non-http(s) values."""
    if value is None:
        return None
    value = value.strip()
    if value and not value.startswith(("http://", "https://")):
        raise ValueError("Must be an http(s) URL")
    return value or None


def optional_email(value: str | None) -> str | None:
    """Normalize an optional email field: strip, validate shape, nix empties."""
    if value is None:
        return None
    value = value.strip()
    if value and not _EMAIL_RE.match(value):
        raise ValueError("Must be a valid email address")
    return value or None


def non_empty_name(value: str, *, max_length: int = 200) -> str:
    value = value.strip()
    if not value:
        raise ValueError("Must not be empty")
    if len(value) > max_length:
        raise ValueError(f"Must be at most {max_length} characters")
    return value


def optional_text(value: str | None, max_length: int) -> str | None:
    """Normalize an optional text field: strip, enforce length, nix empties."""
    if value is None:
        return None
    value = value.strip()
    if len(value) > max_length:
        raise ValueError(f"Must be at most {max_length} characters")
    return value or None