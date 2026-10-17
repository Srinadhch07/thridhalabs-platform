"""Reusable slug generation and validation for content entities.

Policies (apply to clients, projects and testimonials where relevant):

- slugify() produces a lowercase, URL-safe, stable slug from a display name;
  the result is deterministic (same name -> same slug) so callers can rely on
  collision handling at the collection level.
- A caller-supplied slug is validated against a strict pattern rather than
  trusted; anything else is rejected with a controlled AppError.
"""

from __future__ import annotations

import re

from app.core.errors import AppError

_SLUG_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
_MAX_SLUG_LENGTH = 100


def slugify(value: str) -> str:
    """Generate a URL-safe, lowercase slug from arbitrary text.

    "Urban ZoomIN" -> "urban-zoomin"
    "Acme Motors"  -> "acme-motors"
    """
    slug = (value or "").strip().lower()
    slug = re.sub(r"['\"`]", "", slug)  # drop quotes/apostrophes inline
    slug = re.sub(r"[^a-z0-9]+", "-", slug)  # runs of others -> single hyphen
    return slug.strip("-")


def validate_slug(value: str) -> str:
    """Validate a caller-supplied slug; raises AppError 422 when invalid."""
    slug = (value or "").strip().lower()
    if not slug or len(slug) > _MAX_SLUG_LENGTH or not _SLUG_RE.fullmatch(slug):
        raise AppError(
            422,
            "INVALID_SLUG",
            "Slugs may only contain lowercase letters, numbers and single "
            "hyphens, and must be at most 100 characters",
        )
    return slug