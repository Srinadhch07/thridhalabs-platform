"""Pillow composition for 1200x630 social preview images.

Design intent (matches the approved concept): a large image fills the card,
with a legible dark scrim and only minimal provenance text — a small kicker,
the title, an optional one-line subtitle and a branded footer. When the entity
has no usable image a branded fallback canvas is generated instead, so an
`og:image` is always available.

No font files are bundled or loaded from disk: Pillow's built-in scalable
default font is used, which keeps the output identical on every platform
(Windows dev, Linux production) and avoids shipping binaries.
"""

from __future__ import annotations

import io

from PIL import Image, ImageDraw, ImageFont, ImageOps

PREVIEW_WIDTH = 1200
PREVIEW_HEIGHT = 630

_SITE_NAME = "Thridha Labs"
_DEFAULT_BACKGROUND = (7, 9, 16)  # #070910 — the lab's dark canvas
_DEFAULT_ACCENT = (245, 158, 11)  # #f59e0b — amber accent
_TEXT_PRIMARY = (244, 246, 251)
_TEXT_MUTED = (176, 184, 199)

_PADDING = 72
_TEXT_WIDTH = PREVIEW_WIDTH - 2 * _PADDING

_JPEG_QUALITY = 86


def _hex_to_rgb(value: str | None, fallback: tuple[int, int, int]) -> tuple[int, int, int]:
    if not value:
        return fallback
    value = value.strip().lstrip("#")
    if len(value) != 6:
        return fallback
    try:
        return (int(value[0:2], 16), int(value[2:4], 16), int(value[4:6], 16))
    except ValueError:
        return fallback


def _font(size: int) -> ImageFont.ImageFont:
    try:
        return ImageFont.load_default(size=size)
    except TypeError:  # pragma: no cover - very old Pillow
        return ImageFont.load_default()


def _cover_crop(image: Image.Image, width: int, height: int) -> Image.Image:
    """Scale to fill then center-crop — never distorts, never letterboxes."""
    ratio = max(width / image.width, height / image.height)
    new_size = (max(1, round(image.width * ratio)), max(1, round(image.height * ratio)))
    resized = image.resize(new_size, Image.Resampling.LANCZOS)
    left = (resized.width - width) // 2
    top = (resized.height - height) // 2
    return resized.crop((left, top, left + width, top + height))


def _decode_cover(data: bytes) -> Image.Image | None:
    try:
        with Image.open(io.BytesIO(data)) as image:
            image = ImageOps.exif_transpose(image)
            image.load()
            return _cover_crop(image.convert("RGB"), PREVIEW_WIDTH, PREVIEW_HEIGHT)
    except Exception:
        # A broken/absent image must never break the preview route.
        return None


def _fallback_canvas(accent: tuple[int, int, int]) -> Image.Image:
    """A branded dark canvas with a soft diagonal accent wash."""
    canvas = Image.new("RGB", (PREVIEW_WIDTH, PREVIEW_HEIGHT), _DEFAULT_BACKGROUND)
    draw = ImageDraw.Draw(canvas)
    tint = tuple(round(7 + (channel - 7) * 0.32) for channel in accent)
    for x in range(PREVIEW_WIDTH):
        # Diagonal-ish wash: brighter toward the top-right, fading to the base.
        weight = max(0.0, 1.0 - (x / PREVIEW_WIDTH))
        colour = tuple(
            round(_DEFAULT_BACKGROUND[i] + (tint[i] - _DEFAULT_BACKGROUND[i]) * weight)
            for i in range(3)
        )
        draw.line([(x, 0), (x, PREVIEW_HEIGHT)], fill=colour)
    return canvas


def _scrim(base: Image.Image, *, top_alpha: int, bottom_alpha: int) -> Image.Image:
    """Composite a vertical dark gradient so bottom-anchored text stays legible."""
    gradient = Image.linear_gradient("L").resize((PREVIEW_WIDTH, PREVIEW_HEIGHT))
    span = max(1, bottom_alpha - top_alpha)
    mask = gradient.point(lambda v: top_alpha + (v * span) // 255)
    overlay = Image.new("RGB", (PREVIEW_WIDTH, PREVIEW_HEIGHT), (0, 0, 0))
    return Image.composite(overlay, base, mask)


def _wrap(draw: ImageDraw.ImageDraw, text: str, font, max_width: int) -> list[str]:
    words = text.split()
    if not words:
        return []
    lines: list[str] = []
    current = words[0]
    for word in words[1:]:
        candidate = f"{current} {word}"
        if draw.textlength(candidate, font=font) <= max_width:
            current = candidate
        else:
            lines.append(current)
            current = word
    lines.append(current)
    return lines


def _fit(
    draw: ImageDraw.ImageDraw,
    text: str,
    font,
    max_width: int,
    max_lines: int,
) -> list[str]:
    lines = _wrap(draw, text, font, max_width)
    if len(lines) <= max_lines:
        return lines
    lines = lines[:max_lines]
    last = lines[-1]
    while last and draw.textlength(last + "…", font=font) > max_width:
        last = last[:-1].rstrip()
    lines[-1] = (last + "…") if last else "…"
    return lines


def render_preview_image(
    *,
    title: str,
    kicker: str | None = None,
    subtitle: str | None = None,
    footer: str = "",
    background: bytes | None = None,
    accent: str | None = None,
) -> bytes:
    """Render a 1200x630 JPEG preview. Always returns decodable JPEG bytes."""
    accent_rgb = _hex_to_rgb(accent, _DEFAULT_ACCENT)

    decoded = _decode_cover(background) if background else None
    if decoded is not None:
        canvas = _scrim(decoded, top_alpha=40, bottom_alpha=232)
    else:
        canvas = _fallback_canvas(accent_rgb)

    draw = ImageDraw.Draw(canvas)

    title_font = _font(58)
    subtitle_font = _font(32)
    small_font = _font(28)

    # Top accent bar + kicker.
    draw.rectangle([_PADDING, _PADDING, _PADDING + 56, _PADDING + 6], fill=accent_rgb)
    if kicker:
        draw.text(
            (_PADDING, _PADDING + 22),
            kicker.upper(),
            font=small_font,
            fill=accent_rgb,
        )

    footer_text = footer or _SITE_NAME
    footer_h = small_font.size + 6
    footer_y = PREVIEW_HEIGHT - _PADDING - footer_h

    title_lines = _fit(draw, title, title_font, _TEXT_WIDTH, max_lines=2)
    subtitle_lines = (
        _fit(draw, subtitle, subtitle_font, _TEXT_WIDTH, max_lines=2)
        if subtitle
        else []
    )

    title_h = len(title_lines) * (title_font.size + 12)
    subtitle_h = len(subtitle_lines) * (subtitle_font.size + 10)
    gap = 16 if title_lines and subtitle_lines else 0
    block_top = footer_y - 30 - (title_h + gap + subtitle_h)

    y = block_top
    for line in title_lines:
        draw.text((_PADDING, y), line, font=title_font, fill=_TEXT_PRIMARY)
        y += title_font.size + 12
    y += gap
    for line in subtitle_lines:
        draw.text((_PADDING, y), line, font=subtitle_font, fill=_TEXT_MUTED)
        y += subtitle_font.size + 10

    draw.text((_PADDING, footer_y), footer_text, font=small_font, fill=_TEXT_MUTED)

    buffer = io.BytesIO()
    canvas.save(buffer, format="JPEG", quality=_JPEG_QUALITY, optimize=True)
    return buffer.getvalue()
