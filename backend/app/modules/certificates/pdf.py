"""Certificate PDF + QR rendering (pure, synchronous, no I/O).

Kept separate from the service so it can be unit-tested directly and so storage
or database concerns never leak into layout code. The QR code encodes the FULL
public verification URL (never just the id) so a scan lands on the live
verification page.
"""

from __future__ import annotations

import hashlib
import io
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

# Candidate Unicode-capable fonts (best-effort). Falls back to the base-14
# Helvetica family, which is Latin-1 only.
_FONT_CANDIDATES = (
    ("CertSans", r"C:\Windows\Fonts\arial.ttf"),
    ("CertSans", r"C:\Windows\Fonts\segoeui.ttf"),
    ("CertSans", "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"),
    ("CertSans", "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf"),
)
_FONT_BOLD_CANDIDATES = (
    ("CertSansBold", r"C:\Windows\Fonts\arialbd.ttf"),
    ("CertSansBold", r"C:\Windows\Fonts\segoeuib.ttf"),
    ("CertSansBold", "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"),
    ("CertSansBold", "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf"),
)

_fonts_resolved: tuple[str, str] | None = None


def _resolve_fonts() -> tuple[str, str]:
    """Register and return (regular, bold) font names, once per process."""
    global _fonts_resolved
    if _fonts_resolved is not None:
        return _fonts_resolved

    import os

    regular = "Helvetica"
    bold = "Helvetica-Bold"
    for name, path in _FONT_CANDIDATES:
        if os.path.exists(path):
            try:
                pdfmetrics.registerFont(TTFont(name, path))
                regular = name
                break
            except Exception:  # pragma: no cover - corrupt font file
                continue
    for name, path in _FONT_BOLD_CANDIDATES:
        if os.path.exists(path):
            try:
                pdfmetrics.registerFont(TTFont(name, path))
                bold = name
                break
            except Exception:  # pragma: no cover - corrupt font file
                continue
    _fonts_resolved = (regular, bold)
    return _fonts_resolved


def _safe(text: str, font: str) -> str:
    """Drop characters the resolved font cannot encode (Latin-1 fallback)."""
    if font.startswith("CertSans"):
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


def render_certificate_pdf(
    *,
    certificate_id: str,
    member_name: str,
    work_title: str,
    issued_at,
    verification_url: str,
    qr_png: bytes,
    brand_name: str = "Thridha Labs",
    brand_primary: str = "#4f46e5",
    brand_secondary: str = "#0ea5e9",
    brand_text: str = "#0f172a",
    brand_background: str = "#ffffff",
    logo_png: bytes | None = None,
    scope_statement: str = CERTIFICATE_SCOPE_STATEMENT,
) -> bytes:
    regular, bold = _resolve_fonts()
    page = landscape(A4)
    width, height = page

    primary = HexColor(brand_primary)
    secondary = HexColor(brand_secondary)
    text_color = HexColor(brand_text)
    background = HexColor(brand_background) if brand_background != "#ffffff" else white

    buffer = io.BytesIO()
    c = canvas.Canvas(buffer, pagesize=page)
    c.setTitle(f"Thridha Labs Certificate {certificate_id}")
    c.setAuthor(brand_name)
    c.setSubject("Certificate of recognition")
    c.setCreator(brand_name)

    if background is not white:
        c.setFillColor(background)
        c.rect(0, 0, width, height, stroke=0, fill=1)

    margin = 28
    c.setStrokeColor(primary)
    c.setLineWidth(3)
    c.rect(margin, margin, width - 2 * margin, height - 2 * margin)
    c.setStrokeColor(secondary)
    c.setLineWidth(1)
    c.rect(margin + 8, margin + 8, width - 2 * margin - 16, height - 2 * margin - 16)

    center_x = width / 2
    cursor_y = height - 92

    if logo_png:
        try:
            logo = ImageReader(io.BytesIO(logo_png))
            logo_w, logo_h = logo.getSize()
            draw_h = 54
            draw_w = draw_h * (logo_w / logo_h) if logo_h else draw_h
            c.drawImage(
                logo,
                margin + 40,
                height - margin - 78,
                width=draw_w,
                height=draw_h,
                preserveAspectRatio=True,
                mask="auto",
            )
        except Exception:  # pragma: no cover - malformed logo, skip it
            pass

    c.setFillColor(primary)
    c.setFont(bold, 15)
    c.drawCentredString(center_x, cursor_y, _safe(brand_name.upper(), bold))

    cursor_y -= 40
    c.setFillColor(text_color)
    c.setFont(bold, 34)
    c.drawCentredString(center_x, cursor_y, _safe("Certificate of Recognition", bold))

    cursor_y -= 34
    c.setFont(regular, 13)
    c.setFillColor(text_color)
    c.drawCentredString(center_x, cursor_y, "This certificate is presented to")

    cursor_y -= 42
    c.setFillColor(primary)
    c.setFont(bold, 28)
    c.drawCentredString(center_x, cursor_y, _safe(member_name, bold))

    cursor_y -= 32
    c.setStrokeColor(secondary)
    c.setLineWidth(1)
    c.line(center_x - 150, cursor_y, center_x + 150, cursor_y)

    cursor_y -= 34
    c.setFillColor(text_color)
    c.setFont(regular, 13)
    c.drawCentredString(
        center_x, cursor_y, "in recognition of the reviewed work"
    )

    cursor_y -= 30
    c.setFont(bold, 18)
    title_lines = _wrap(_safe(work_title, bold), bold, 18, width - 260)
    for line in title_lines[:2]:
        c.drawCentredString(center_x, cursor_y, line)
        cursor_y -= 22

    # Issued date
    issued_str = issued_at.strftime("%d %B %Y") if issued_at else ""
    if issued_str:
        cursor_y -= 10
        c.setFont(regular, 12)
        c.setFillColor(text_color)
        c.drawCentredString(center_x, cursor_y, f"Issued on {issued_str}")

    # QR block (bottom-left) + scope statement.
    qr_size = 108
    qr_x = margin + 46
    qr_y = margin + 52
    c.drawImage(
        ImageReader(io.BytesIO(qr_png)),
        qr_x,
        qr_y,
        width=qr_size,
        height=qr_size,
        preserveAspectRatio=True,
        mask="auto",
    )
    c.setFont(regular, 9)
    c.setFillColor(text_color)
    c.drawString(qr_x, qr_y - 14, "Scan to verify")

    # Certificate id + URL (bottom-right).
    right_x = width - margin - 46
    c.setFont(bold, 11)
    c.drawRightString(right_x, margin + 128, f"Certificate ID: {certificate_id}")
    c.setFont(regular, 8)
    c.drawRightString(right_x, margin + 114, verification_url)

    # Scope disclaimer (small print, centred above the bottom border).
    scope_lines = _wrap(_safe(scope_statement, regular), regular, 8, width - 2 * margin - 220)
    scope_y = margin + 40
    c.setFillColor(text_color)
    c.setFont(regular, 8)
    for line in scope_lines:
        c.drawCentredString(center_x, scope_y, line)
        scope_y -= 10

    c.showPage()
    c.save()
    return buffer.getvalue()
