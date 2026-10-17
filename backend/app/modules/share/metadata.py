"""Pure HTML rendering for social share documents.

Kept free of FastAPI, database and storage concerns so it can be unit-tested
directly. Every interpolated value is HTML-escaped: titles and bios are
user-controlled content and must never break out of an attribute or element.
"""

from __future__ import annotations

import html
from dataclasses import dataclass, field

SITE_NAME = "Thridha Labs"
DEFAULT_DESCRIPTION = (
    "Thridha Labs is a technology and AI experimentation lab. AI, software and "
    "ideas turned into things people can actually use."
)

# Social platforms truncate around here; keep previews tidy and predictable.
MAX_DESCRIPTION = 200
MAX_TITLE = 120


@dataclass(frozen=True)
class ShareCard:
    """Resolved metadata for a single shareable public URL.

    `kind` is one of ``member`` | ``project`` | ``work`` and only affects the
    Open Graph type / labels, never visibility.
    """

    kind: str
    title: str
    description: str | None
    canonical_url: str
    image_url: str
    image_alt: str
    og_type: str
    robots: str = "index, follow"
    site_name: str = SITE_NAME
    # Presentation hints used only when rendering the preview image.
    kicker: str | None = None
    subtitle: str | None = None
    footer: str = field(default="")


def _esc(value: str) -> str:
    return html.escape(value, quote=True)


def _collapse(value: str) -> str:
    return " ".join(value.split())


def _truncate(value: str, limit: int) -> str:
    value = value.strip()
    if len(value) <= limit:
        return value
    # Prefer a word boundary when one is close to the limit.
    clipped = value[: limit - 1]
    boundary = clipped.rfind(" ")
    if boundary >= limit - 20:
        clipped = clipped[:boundary]
    return clipped.rstrip(" ,;:.-") + "…"


def clean_title(value: str) -> str:
    cleaned = _collapse(value)
    return cleaned or SITE_NAME


def clean_description(value: str | None) -> str:
    if not value:
        return DEFAULT_DESCRIPTION
    cleaned = _collapse(value)
    return _truncate(cleaned, MAX_DESCRIPTION) if cleaned else DEFAULT_DESCRIPTION


def _meta(attribute: str, key: str, content: str) -> str:
    return f'    <meta {attribute}="{_esc(key)}" content="{_esc(content)}">'


def render_share_html(card: ShareCard) -> str:
    """Return a complete, standalone HTML document carrying the social metadata.

    It is intentionally self-contained: crawlers that ignore the SPA still read
    the Open Graph / Twitter tags, while human visitors (who should normally be
    routed to the SPA by the proxy) get a readable summary and a link back to
    the canonical page. No redirect is emitted — a meta refresh here would risk
    a crawl loop through the proxy rewrite.
    """
    title = clean_title(card.title)
    description = clean_description(card.description)
    canonical = card.canonical_url
    image = card.image_url
    alt = _collapse(card.image_alt) or title

    lines = [
        "<!doctype html>",
        '<html lang="en">',
        "  <head>",
        '    <meta charset="utf-8">',
        '    <meta name="viewport" content="width=device-width, initial-scale=1">',
        f"    <title>{_esc(title)}</title>",
        _meta("name", "description", description),
        f'    <link rel="canonical" href="{_esc(canonical)}">',
        _meta("name", "robots", card.robots),
        _meta("property", "og:site_name", card.site_name),
        _meta("property", "og:type", card.og_type),
        _meta("property", "og:title", title),
        _meta("property", "og:description", description),
        _meta("property", "og:url", canonical),
        _meta("property", "og:image", image),
        _meta("property", "og:image:secure_url", image),
        _meta("property", "og:image:type", "image/jpeg"),
        _meta("property", "og:image:width", "1200"),
        _meta("property", "og:image:height", "630"),
        _meta("property", "og:image:alt", alt),
        _meta("name", "twitter:card", "summary_large_image"),
        _meta("name", "twitter:title", title),
        _meta("name", "twitter:description", description),
        _meta("name", "twitter:image", image),
        _meta("name", "twitter:image:alt", alt),
        "  </head>",
        "  <body>",
        "    <main>",
        f"      <h1>{_esc(title)}</h1>",
        f"      <p>{_esc(description)}</p>",
        (
            f'      <img src="{_esc(image)}" alt="{_esc(alt)}" '
            'width="1200" height="630">'
        ),
        f'      <p><a href="{_esc(canonical)}">View on {_esc(card.site_name)}</a></p>',
        "    </main>",
        "  </body>",
        "</html>",
        "",
    ]
    return "\n".join(lines)


def render_not_found_html(site_name: str = SITE_NAME) -> str:
    """A minimal 404 document for unknown/private share targets.

    Deliberately identical for every not-found case: an unpublished work and a
    non-existent member must not be distinguishable (no existence leak).
    """
    return "\n".join(
        [
            "<!doctype html>",
            '<html lang="en">',
            "  <head>",
            '    <meta charset="utf-8">',
            f"    <title>Not found — {_esc(site_name)}</title>",
            _meta("name", "robots", "noindex, nofollow"),
            _meta("name", "description", "This page is not available."),
            "  </head>",
            "  <body>",
            "    <main>",
            "      <h1>Not found</h1>",
            "      <p>This page is not available.</p>",
            f'      <p><a href="/">{_esc(site_name)}</a></p>',
            "    </main>",
            "  </body>",
            "</html>",
            "",
        ]
    )
