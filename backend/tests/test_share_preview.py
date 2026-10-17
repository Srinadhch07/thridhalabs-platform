"""Pure unit tests for the social share HTML + preview image generation.

These do not touch MongoDB, storage or the ASGI app — they exercise the
rendering primitives directly so they run fast and deterministically.
"""

from __future__ import annotations

import io

from PIL import Image

from app.modules.share.metadata import (
    ShareCard,
    clean_description,
    render_not_found_html,
    render_share_html,
)
from app.modules.share.preview import PREVIEW_HEIGHT, PREVIEW_WIDTH, render_preview_image
from tests._content_helpers import png_bytes

_REQUIRED_META = (
    "og:title",
    "og:description",
    "og:image",
    "og:image:alt",
    "og:url",
    "og:type",
    "twitter:card",
    "twitter:title",
    "twitter:description",
    "twitter:image",
    "twitter:image:alt",
)


def _card() -> ShareCard:
    return ShareCard(
        kind="work",
        title="Aurora Dashboard — Thridha Labs",
        description="An analytics dashboard built for a real client.",
        canonical_url="https://thridhalabs.example/members/THL-M-2026-0001/works/aurora",
        image_url="https://thridhalabs.example/share/members/THL-M-2026-0001/works/aurora/image",
        image_alt="Cover image for Aurora Dashboard",
        og_type="article",
    )


def test_share_html_contains_all_required_metadata():
    html = render_share_html(_card())
    for key in _REQUIRED_META:
        assert key in html, key
    assert "summary_large_image" in html
    assert 'rel="canonical"' in html
    assert "https://thridhalabs.example/members/THL-M-2026-0001/works/aurora" in html
    assert "og:image:width" in html and "og:image:height" in html
    assert ('content="1200"' in html) and ('content="630"' in html)


def test_share_html_escapes_user_controlled_values():
    card = ShareCard(
        kind="member",
        title='Ada <script>alert(1)</script> "Lovelace"',
        description="Bio with <b>markup</b> & an ampersand",
        canonical_url="https://thridhalabs.example/members/THL-M-1",
        image_url="https://thridhalabs.example/share/members/THL-M-1/image",
        image_alt='Portrait of "Ada"',
        og_type="profile",
    )
    html = render_share_html(card)
    assert "<script>" not in html
    assert "&lt;script&gt;" in html
    assert "&amp;" in html
    assert 'content="Portrait of &quot;Ada&quot;"' in html


def test_not_found_html_is_noindex_and_generic():
    html = render_not_found_html()
    assert "noindex, nofollow" in html
    assert "Not found" in html
    # No entity-specific detail can ever appear here (existence is not leaked).
    assert "THL-M" not in html


def test_clean_description_collapses_and_truncates():
    assert clean_description(None) != ""
    long_text = "word " * 200
    result = clean_description(long_text)
    assert len(result) <= 201
    assert result.endswith("…")
    assert "  " not in clean_description("a\n\n  b   c")


def test_render_preview_image_fallback_is_1200x630_jpeg():
    data = render_preview_image(
        title="Ada Lovelace",
        kicker="Member · THL-M-2026-0001",
        subtitle="Backend engineer",
        footer="thridhalabs.example",
        background=None,
        accent="#f59e0b",
    )
    image = Image.open(io.BytesIO(data))
    assert image.format == "JPEG"
    assert image.size == (PREVIEW_WIDTH, PREVIEW_HEIGHT)


def test_render_preview_image_with_photo_keeps_dimensions():
    data = render_preview_image(
        title="Project With Cover",
        kicker="Project",
        subtitle="A client platform",
        footer="thridhalabs.example",
        background=png_bytes(400, 900, "teal"),
        accent="#0ea5e9",
    )
    image = Image.open(io.BytesIO(data))
    assert image.format == "JPEG"
    assert image.size == (PREVIEW_WIDTH, PREVIEW_HEIGHT)


def test_render_preview_image_tolerates_corrupt_background():
    data = render_preview_image(
        title="Broken", background=b"not-an-image", accent="#f59e0b"
    )
    assert Image.open(io.BytesIO(data)).size == (PREVIEW_WIDTH, PREVIEW_HEIGHT)
