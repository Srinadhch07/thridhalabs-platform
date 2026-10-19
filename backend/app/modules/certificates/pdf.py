"""Certificate PDF + QR rendering (pure, synchronous, no I/O).

Kept separate from the service so it can be unit-tested directly and so storage
or database concerns never leak into layout code. The QR code encodes the FULL
public verification URL (never just the id) so a scan lands on the live
verification page.

The visual design is a premium landscape certificate: warm ivory paper, a fine
pale-gold frame, restrained gold corner line-work, a left-aligned editorial
content column, and a dedicated right-hand QR verification column. It carries
no signature or signatory block by design.
"""

from __future__ import annotations

import hashlib
import io
import os
import secrets

import qrcode
from reportlab.lib.colors import HexColor, white
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.utils import ImageReader
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas

from app.models.certificate import (
    CERTIFICATE_ID_ALPHABET,
    CERTIFICATE_ID_PREFIX,
    CERTIFICATE_ID_RANDOM_LENGTH,
    CERTIFICATE_SCOPE_STATEMENT,
)

# --------------------------------------------------------------------------- #
# Design palette — a fixed, deliberately art-directed premium palette. It is
# intentionally independent of the runtime brand colours: the certificate has
# its own ivory-and-gold identity that reads consistently in every deployment.
# --------------------------------------------------------------------------- #
IVORY = HexColor("#F8F3EA")       # warm paper background
CHARCOAL = HexColor("#18202A")    # primary text
GOLD = HexColor("#B38A4B")        # accent
GOLD_FINE = HexColor("#D7B77E")   # fine decorative line-work
MUTED = HexColor("#6D675F")       # secondary text

# --------------------------------------------------------------------------- #
# Layout geometry (A4 landscape = 841.89 x 595.28 pt; 1 mm ≈ 2.835 pt)
# --------------------------------------------------------------------------- #
PAGE_WIDTH = 841.89
FRAME_INSET = 18.0          # ≈ 6.3 mm pale-gold frame inset
CONTENT_LEFT = 76.0
CONTENT_RIGHT = PAGE_WIDTH - 76.0
DIVIDER_X = 560.0           # vertical gold rule between content and verify column
GUTTER = 28.0               # breathing room either side of the divider
MAIN_WIDTH = DIVIDER_X - CONTENT_LEFT - GUTTER
CORNER_RADII = (20.0, 32.0, 44.0)
CORNER_CENTRE = 26.0

# Brand lockup (logo + wordmark) geometry. The logo and wordmark share a single
# vertical centre so they read as one carefully aligned lockup rather than two
# unrelated elements.
BRAND_CENTER_Y = 512.0        # shared vertical centre of the whole lockup
BRAND_LOGO_MAX_H = 28.0       # logo is scaled to fit inside this box…
BRAND_LOGO_MAX_W = 120.0      # …and never wider than this (wide logos stay safe)
BRAND_GAP = 13.0              # horizontal gap between the logo and the wordmark
BRAND_WORDMARK_SIZE = 16.0
BRAND_WORDMARK_TRACKING = 1.6
BRAND_RULE_GAP = 13.0         # gold rule distance below the lockup
# Times New Roman cap-height (U+0041–U+005A) as a fraction of the em size; used
# to optically centre the all-caps wordmark on the shared lockup centre.
TIMES_CAP_RATIO = 0.662

# --------------------------------------------------------------------------- #
# Fonts — best-effort Unicode faces with base-14 fallbacks. TTF availability is
# probed per platform (Windows Arial/Segoe/Georgia/Times, Linux DejaVu/Liberation)
# and any face that fails to register falls back to the matching base-14 family.
# --------------------------------------------------------------------------- #
_FONT_SPECS: dict[str, tuple[str, tuple[tuple[str, str], ...]]] = {
    "sans": (
        "Helvetica",
        (
            ("CertSans", r"C:\Windows\Fonts\arial.ttf"),
            ("CertSans", r"C:\Windows\Fonts\segoeui.ttf"),
            ("CertSans", "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"),
            ("CertSans", "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf"),
        ),
    ),
    "sans_bold": (
        "Helvetica-Bold",
        (
            ("CertSansBold", r"C:\Windows\Fonts\arialbd.ttf"),
            ("CertSansBold", r"C:\Windows\Fonts\segoeuib.ttf"),
            ("CertSansBold", "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"),
            ("CertSansBold", "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf"),
        ),
    ),
    "serif": (
        "Times-Roman",
        (
            ("CertSerif", r"C:\Windows\Fonts\georgia.ttf"),
            ("CertSerif", r"C:\Windows\Fonts\times.ttf"),
            ("CertSerif", "/usr/share/fonts/truetype/dejavu/DejaVuSerif.ttf"),
            ("CertSerif", "/usr/share/fonts/truetype/liberation/LiberationSerif-Regular.ttf"),
        ),
    ),
    "serif_bold": (
        "Times-Bold",
        (
            ("CertSerifBold", r"C:\Windows\Fonts\georgiab.ttf"),
            ("CertSerifBold", r"C:\Windows\Fonts\timesbd.ttf"),
            ("CertSerifBold", "/usr/share/fonts/truetype/dejavu/DejaVuSerif-Bold.ttf"),
            ("CertSerifBold", "/usr/share/fonts/truetype/liberation/LiberationSerif-Bold.ttf"),
        ),
    ),
    # Dedicated Times New Roman faces for the brand wordmark only. Times New
    # Roman is a serif face; the base-14 "Times-Roman"/"Times-Bold" fallbacks are
    # metrically Times, so the wordmark is Times even where no TTF is installed.
    "times": (
        "Times-Roman",
        (
            ("CertTimes", r"C:\Windows\Fonts\times.ttf"),
            ("CertTimes", "/usr/share/fonts/truetype/msttcorefonts/Times_New_Roman.ttf"),
            ("CertTimes", "/usr/share/fonts/truetype/liberation/LiberationSerif-Regular.ttf"),
        ),
    ),
    "times_bold": (
        "Times-Bold",
        (
            ("CertTimesBold", r"C:\Windows\Fonts\timesbd.ttf"),
            ("CertTimesBold", "/usr/share/fonts/truetype/msttcorefonts/Times_New_Roman_Bold.ttf"),
            ("CertTimesBold", "/usr/share/fonts/truetype/liberation/LiberationSerif-Bold.ttf"),
        ),
    ),
    "mono": ("Courier", ()),
    "mono_bold": ("Courier-Bold", ()),
}

_fonts_resolved: dict[str, str] | None = None
_unicode_fonts: set[str] = set()


def _resolve_fonts() -> dict[str, str]:
    """Register and return the font face names, once per process."""
    global _fonts_resolved
    if _fonts_resolved is not None:
        return _fonts_resolved

    resolved: dict[str, str] = {}
    for key, (fallback, candidates) in _FONT_SPECS.items():
        name = fallback
        for face, path in candidates:
            if os.path.exists(path):
                try:
                    pdfmetrics.registerFont(TTFont(face, path))
                    _unicode_fonts.add(face)
                    name = face
                    break
                except Exception:  # pragma: no cover - corrupt font file
                    continue
        resolved[key] = name
    _fonts_resolved = resolved
    return resolved


def _safe(text: str, font: str) -> str:
    """Drop characters the resolved font cannot encode (Latin-1 fallback)."""
    if font in _unicode_fonts:
        return text
    try:
        text.encode("latin-1")
        return text
    except UnicodeEncodeError:
        return text.encode("latin-1", "replace").decode("latin-1")


def generate_certificate_id(year: int) -> str:
    """`THL-CERT-<year>-<12 random unambiguous chars>` (≈60 bits of entropy)."""
    suffix = "".join(
        secrets.choice(CERTIFICATE_ID_ALPHABET)
        for _ in range(CERTIFICATE_ID_RANDOM_LENGTH)
    )
    return f"{CERTIFICATE_ID_PREFIX}-{year}-{suffix}"


def build_verification_url(base_url: str, certificate_id: str) -> str:
    return f"{base_url.rstrip('/')}/verify-certificate/{certificate_id}"


def generate_qr_png(data: str) -> bytes:
    qr = qrcode.QRCode(
        version=None,
        error_correction=qrcode.constants.ERROR_CORRECT_M,
        box_size=8,
        border=2,
    )
    qr.add_data(data)
    qr.make(fit=True)
    image = qr.make_image(fill_color="black", back_color="white").convert("RGB")
    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    return buffer.getvalue()


def sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


# --------------------------------------------------------------------------- #
# Low-level drawing helpers
# --------------------------------------------------------------------------- #
def _wrap(text: str, font: str, size: float, max_width: float) -> list[str]:
    words = text.split()
    lines: list[str] = []
    current = ""
    for word in words:
        candidate = f"{current} {word}".strip()
        if pdfmetrics.stringWidth(candidate, font, size) <= max_width or not current:
            current = candidate
        else:
            lines.append(current)
            current = word
    if current:
        lines.append(current)
    return lines


def _fit_size(
    text: str, font: str, size: float, max_width: float, minimum: float
) -> float:
    """Shrink a single-line string until it fits, down to `minimum`."""
    current = size
    while current > minimum and pdfmetrics.stringWidth(text, font, current) > max_width:
        current -= 0.5
    return current


def _tracked_width(text: str, font: str, size: float, tracking: float) -> float:
    return pdfmetrics.stringWidth(text, font, size) + tracking * max(0, len(text) - 1)


def _draw_tracked(
    c: canvas.Canvas,
    x: float,
    y: float,
    text: str,
    *,
    font: str,
    size: float,
    color: HexColor,
    tracking: float = 0.0,
    align: str = "left",
) -> float:
    """Draw (optionally letter-spaced) text; returns the drawn width."""
    width = _tracked_width(text, font, size, tracking)
    if align == "center":
        x -= width / 2
    elif align == "right":
        x -= width
    # Contain the letter-spacing (`Tc`) inside a save/restore graphics state.
    # PDF text state is part of the graphics state, so without this the tracking
    # would leak into every later plain drawString/drawCentredString call and
    # inflate real glyph widths beyond what _wrap/_fit_size measured.
    c.saveState()
    c.setFillColor(color)
    text_obj = c.beginText(x, y)
    text_obj.setFont(font, size)
    if tracking:
        text_obj.setCharSpace(tracking)
    text_obj.textOut(_safe(text, font))
    c.drawText(text_obj)
    c.restoreState()
    return width


def _to_image_reader(data: bytes | None) -> ImageReader | None:
    """Normalise arbitrary image bytes (e.g. stored WebP logos) to a reader.

    Media uploads are transcoded to WebP, which ReportLab cannot always decode;
    re-encoding through Pillow first makes the existing brand logo render
    reliably. Transparent padding is trimmed to the visible mark so the logo
    aligns exactly with the content margin and is not scaled down by empty
    borders (the mark's own transparency is preserved). Returns ``None`` if the
    payload is unusable.
    """
    if not data:
        return None
    try:
        from PIL import Image

        image = Image.open(io.BytesIO(data))
        image.load()
        image = _trim_transparent(image)
        normalised = io.BytesIO()
        image.save(normalised, format="PNG")
        normalised.seek(0)
        return ImageReader(normalised)
    except Exception:
        try:
            return ImageReader(io.BytesIO(data))
        except Exception:  # pragma: no cover - unusable image bytes
            return None


def _trim_transparent(image):
    """Crop fully transparent borders from an image, if it carries alpha."""
    try:
        if "A" in image.getbands():
            bbox = image.getchannel("A").getbbox()
            if bbox and bbox != (0, 0, *image.size):
                return image.crop(bbox)
    except Exception:  # pragma: no cover - defensive
        pass
    return image


def _draw_background(c: canvas.Canvas, width: float, height: float) -> None:
    c.setFillColor(IVORY)
    c.rect(0, 0, width, height, stroke=0, fill=1)


def _draw_frame(c: canvas.Canvas, width: float, height: float) -> None:
    """A single fine pale-gold outer rule with a hairline inner echo."""
    c.setStrokeColor(GOLD_FINE)
    c.setLineWidth(1.1)
    c.rect(
        FRAME_INSET,
        FRAME_INSET,
        width - 2 * FRAME_INSET,
        height - 2 * FRAME_INSET,
        stroke=1,
        fill=0,
    )
    c.setLineWidth(0.5)
    c.rect(
        FRAME_INSET + 4.5,
        FRAME_INSET + 4.5,
        width - 2 * FRAME_INSET - 9,
        height - 2 * FRAME_INSET - 9,
        stroke=1,
        fill=0,
    )


def _corner_arcs(c: canvas.Canvas, cx: float, cy: float, start_angle: float) -> None:
    for radius in CORNER_RADII:
        c.arc(
            cx - radius,
            cy - radius,
            cx + radius,
            cy + radius,
            startAng=start_angle,
            extent=90,
        )


def _draw_corner_linework(c: canvas.Canvas, width: float, height: float) -> None:
    """Restrained concentric-gold arcs tucked into two opposite corners."""
    c.saveState()
    c.setStrokeAlpha(0.5)
    c.setFillAlpha(0.7)
    c.setStrokeColor(GOLD_FINE)
    c.setLineWidth(0.6)

    _corner_arcs(c, CORNER_CENTRE, CORNER_CENTRE, 0.0)
    _corner_arcs(c, width - CORNER_CENTRE, height - CORNER_CENTRE, 180.0)

    c.setFillColor(GOLD)
    c.circle(CORNER_CENTRE, CORNER_CENTRE, 1.5, stroke=0, fill=1)
    c.circle(width - CORNER_CENTRE, height - CORNER_CENTRE, 1.5, stroke=0, fill=1)
    c.restoreState()


def _draw_calendar_icon(
    c: canvas.Canvas, x: float, y: float, size: float, color: HexColor
) -> None:
    """A minimal calendar glyph (body, header rule and two binder ticks)."""
    c.saveState()
    c.setStrokeColor(color)
    c.setFillColor(color)
    c.setLineWidth(0.9)
    body_top = y + size
    c.roundRect(x, y, size, size, 1.5, stroke=1, fill=0)
    c.line(x, body_top - size * 0.3, x + size, body_top - size * 0.3)
    tick = size * 0.18
    c.line(x + size * 0.3, body_top, x + size * 0.3, body_top + tick)
    c.line(x + size * 0.7, body_top, x + size * 0.7, body_top + tick)
    c.circle(x + size * 0.32, y + size * 0.32, 0.7, stroke=0, fill=1)
    c.circle(x + size * 0.68, y + size * 0.32, 0.7, stroke=0, fill=1)
    c.restoreState()


def _brand_wordmark(name: str) -> str:
    """Uppercase the brand, keeping the canonical 'THRIDHA LABS' spacing."""
    cleaned = (name or "Thridha Labs").strip()
    if cleaned.lower().replace(" ", "") == "thridhalabs":
        return "THRIDHA LABS"
    return cleaned.upper()


def _draw_brand_lockup(
    c: canvas.Canvas,
    *,
    brand_name: str,
    logo_png: bytes | None,
    wordmark_font: str,
) -> None:
    """Draw the logo + wordmark as a single, vertically centred brand lockup.

    The logo is scaled to fit ``BRAND_LOGO_MAX_H`` x ``BRAND_LOGO_MAX_W`` with its
    aspect ratio preserved (arbitrary logo dimensions are handled safely, and
    transparent backgrounds are honoured), then vertically centred on the same
    axis as the all-caps wordmark. The whole group starts at the main content
    margin (``CONTENT_LEFT``). A hairline gold rule is drawn beneath the group.
    """
    wordmark = _brand_wordmark(brand_name)
    reader = _to_image_reader(logo_png)

    logo_w = logo_h = 0.0
    if reader is not None:
        image_w, image_h = reader.getSize()
        if image_w > 0 and image_h > 0:
            scale = min(BRAND_LOGO_MAX_H / image_h, BRAND_LOGO_MAX_W / image_w)
            logo_w = image_w * scale
            logo_h = image_h * scale
            c.drawImage(
                reader,
                CONTENT_LEFT,
                BRAND_CENTER_Y - logo_h / 2.0,
                width=logo_w,
                height=logo_h,
                preserveAspectRatio=True,
                mask="auto",
            )

    wordmark_x = CONTENT_LEFT + (logo_w + BRAND_GAP if logo_w else 0.0)
    # Optically centre the all-caps wordmark on the shared lockup centre.
    baseline = BRAND_CENTER_Y - BRAND_WORDMARK_SIZE * TIMES_CAP_RATIO / 2.0
    wordmark_w = _draw_tracked(
        c,
        wordmark_x,
        baseline,
        wordmark,
        font=wordmark_font,
        size=BRAND_WORDMARK_SIZE,
        color=CHARCOAL,
        tracking=BRAND_WORDMARK_TRACKING,
    )

    group_bottom = BRAND_CENTER_Y - (logo_h / 2.0 if logo_h else BRAND_WORDMARK_SIZE * 0.35)
    c.setStrokeColor(GOLD_FINE)
    c.setLineWidth(0.9)
    c.line(CONTENT_LEFT, group_bottom - BRAND_RULE_GAP, wordmark_x + wordmark_w,
           group_bottom - BRAND_RULE_GAP)


# --------------------------------------------------------------------------- #
# Certificate composition
# --------------------------------------------------------------------------- #
def render_certificate_pdf(
    *,
    certificate_id: str,
    member_name: str,
    work_title: str,
    issued_at,
    verification_url: str,
    qr_png: bytes,
    brand_name: str = "Thridha Labs",
    logo_png: bytes | None = None,
    scope_statement: str = CERTIFICATE_SCOPE_STATEMENT,
) -> bytes:
    fonts = _resolve_fonts()
    sans, sans_bold = fonts["sans"], fonts["sans_bold"]
    serif, serif_bold = fonts["serif"], fonts["serif_bold"]
    mono = fonts["mono"]
    wordmark_font = fonts["times_bold"]

    page = landscape(A4)
    width, height = page

    buffer = io.BytesIO()
    c = canvas.Canvas(buffer, pagesize=page)
    c.setTitle(f"Thridha Labs Certificate {certificate_id}")
    c.setAuthor(brand_name or "Thridha Labs")
    c.setSubject("Certificate of Recognition")
    c.setCreator(brand_name or "Thridha Labs")

    _draw_background(c, width, height)
    _draw_frame(c, width, height)
    _draw_corner_linework(c, width, height)

    # ---- Brand lockup: existing logo + Times New Roman wordmark, top-left ----
    _draw_brand_lockup(
        c,
        brand_name=brand_name,
        logo_png=logo_png,
        wordmark_font=wordmark_font,
    )

    # ---- Certificate heading (serif, dominant, left-aligned) ----
    heading = "Certificate of Recognition"
    heading_size = _fit_size(heading, serif_bold, 31.0, MAIN_WIDTH, 22.0)
    c.setFillColor(CHARCOAL)
    c.setFont(serif_bold, heading_size)
    c.drawString(CONTENT_LEFT, 424, _safe(heading, serif_bold))

    # ---- Recipient introduction ----
    c.setFillColor(MUTED)
    c.setFont(sans, 12.5)
    c.drawString(CONTENT_LEFT, 384, "This certificate is presented to")

    # ---- Recipient name (dominant after the heading) ----
    name_text = _safe(member_name, serif_bold)
    name_size = _fit_size(name_text, serif_bold, 28.0, MAIN_WIDTH, 19.0)
    if pdfmetrics.stringWidth(name_text, serif_bold, name_size) <= MAIN_WIDTH:
        name_lines = [name_text]
    else:
        name_lines = _wrap(name_text, serif_bold, name_size, MAIN_WIDTH)
    name_y = 330.0
    c.setFillColor(CHARCOAL)
    c.setFont(serif_bold, name_size)
    for line in name_lines:
        c.drawString(CONTENT_LEFT, name_y, line)
        name_y -= name_size * 1.05
    name_bottom = name_y + name_size * 0.04

    # ---- Thin gold divider beneath the name ----
    divider_y = name_bottom - 24
    c.setStrokeColor(GOLD)
    c.setLineWidth(1.3)
    c.line(CONTENT_LEFT, divider_y, CONTENT_LEFT + 280, divider_y)

    # ---- Recognition statement ----
    c.setFillColor(MUTED)
    c.setFont(sans, 12.5)
    c.drawString(CONTENT_LEFT, divider_y - 30, "In recognition of the reviewed work")

    # ---- Work / programme title (subordinate to the name, wraps) ----
    title_text = _safe(work_title, sans_bold)
    title_size = _fit_size(title_text, sans_bold, 17.0, MAIN_WIDTH, 13.0)
    title_lines = _wrap(title_text, sans_bold, title_size, MAIN_WIDTH)
    title_y = divider_y - 62
    c.setFillColor(CHARCOAL)
    c.setFont(sans_bold, title_size)
    for line in title_lines:
        c.drawString(CONTENT_LEFT, title_y, line)
        title_y -= title_size * 1.28

    # ---- Verification column (right) ----
    _draw_verification_column(
        c,
        width=width,
        qr_png=qr_png,
        issued_at=issued_at,
        certificate_id=certificate_id,
        sans=sans,
        sans_bold=sans_bold,
        mono=mono,
    )

    # ---- Footer ----
    _draw_footer(c, width, sans, sans_bold, brand_name)

    # ---- Existing scope disclaimer, retained as fine print ----
    _draw_scope_note(c, width, sans, scope_statement)

    c.showPage()
    c.save()
    return buffer.getvalue()


def _draw_verification_column(
    c: canvas.Canvas,
    *,
    width: float,
    qr_png: bytes,
    issued_at,
    certificate_id: str,
    sans: str,
    sans_bold: str,
    mono: str,
) -> None:
    verify_left = DIVIDER_X + GUTTER
    verify_right = width - 76.0
    center = (verify_left + verify_right) / 2

    # vertical gold divider running from the heading down to above the footer
    div_top = 470.0
    div_bottom = 92.0
    c.setStrokeColor(GOLD_FINE)
    c.setLineWidth(0.9)
    c.line(DIVIDER_X, div_bottom, DIVIDER_X, div_top)

    # upper-endpoint marker (ring + solid hub)
    c.setStrokeColor(GOLD_FINE)
    c.setLineWidth(0.8)
    c.circle(DIVIDER_X, div_top, 4.4, stroke=1, fill=0)
    c.setFillColor(GOLD)
    c.circle(DIVIDER_X, div_top, 2.4, stroke=0, fill=1)

    # ---- QR code on a white quiet zone ----
    qr_size = 78.0
    pad = 7.0
    qr_top = 452.0
    qr_x = center - qr_size / 2
    qr_y = qr_top - qr_size
    c.setFillColor(white)
    c.setStrokeColor(GOLD_FINE)
    c.setLineWidth(0.7)
    c.roundRect(
        qr_x - pad,
        qr_y - pad,
        qr_size + 2 * pad,
        qr_size + 2 * pad,
        3,
        stroke=1,
        fill=1,
    )
    c.drawImage(
        ImageReader(io.BytesIO(qr_png)),
        qr_x,
        qr_y,
        width=qr_size,
        height=qr_size,
        preserveAspectRatio=True,
        mask="auto",
    )

    # ---- "Verify Certificate" label directly beneath the code ----
    _draw_tracked(
        c,
        center,
        qr_y - 26,
        "Verify Certificate",
        font=sans_bold,
        size=9.5,
        color=CHARCOAL,
        tracking=1.4,
        align="center",
    )

    # ---- Issue date (gold calendar marker + date) ----
    issued_str = issued_at.strftime("%d %B %Y") if issued_at else ""
    date_y = qr_y - 62
    if issued_str:
        icon = 11.0
        gap = 7.0
        text_w = pdfmetrics.stringWidth(issued_str, sans, 11.5)
        group_w = icon + gap + text_w
        start_x = center - group_w / 2
        _draw_calendar_icon(c, start_x, date_y - 1, icon, GOLD)
        c.setFillColor(CHARCOAL)
        c.setFont(sans, 11.5)
        c.drawString(start_x + icon + gap, date_y, _safe(issued_str, sans))

    # ---- Certificate identifier ----
    id_label_y = date_y - 34
    _draw_tracked(
        c,
        center,
        id_label_y,
        "CERTIFICATE ID",
        font=sans,
        size=7.5,
        color=MUTED,
        tracking=1.6,
        align="center",
    )
    id_font_size = _fit_size(certificate_id, mono, 9.0, verify_right - verify_left, 0.0)
    id_lines = _wrap(certificate_id, mono, id_font_size, verify_right - verify_left)
    id_y = id_label_y - 15
    c.setFillColor(CHARCOAL)
    c.setFont(mono, id_font_size)
    for line in id_lines:
        c.drawCentredString(center, id_y, _safe(line, mono))
        id_y -= id_font_size * 1.3


def _draw_footer(
    c: canvas.Canvas, width: float, sans: str, sans_bold: str, brand_name: str
) -> None:
    right = width - 76.0
    c.setStrokeColor(GOLD_FINE)
    c.setLineWidth(0.6)
    c.line(CONTENT_LEFT, 68.0, right, 68.0)

    _draw_tracked(
        c,
        CONTENT_LEFT,
        50.0,
        "OFFICIAL DIGITAL CERTIFICATE",
        font=sans,
        size=8,
        color=MUTED,
        tracking=1.6,
    )
    _draw_tracked(
        c,
        right,
        50.0,
        _brand_wordmark(brand_name),
        font=sans_bold,
        size=8,
        color=GOLD,
        tracking=1.6,
        align="right",
    )


def _draw_scope_note(
    c: canvas.Canvas, width: float, sans: str, scope_statement: str
) -> None:
    """Existing legal disclaimer, kept as restrained fine print near the edge."""
    text = _safe(scope_statement, sans)
    max_width = width - 2 * CONTENT_LEFT
    size = 6.4
    lines = _wrap(text, sans, size, max_width)
    while len(lines) > 2 and size > 5.0:
        size -= 0.2
        lines = _wrap(text, sans, size, max_width)
    y = 36.0
    c.setFillColor(MUTED)
    c.setFont(sans, size)
    for line in lines:
        c.drawCentredString(width / 2, y, line)
        y -= size * 1.28
