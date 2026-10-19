"""Activity certificate PDF + QR rendering (pure, synchronous, no I/O).

A distinct renderer from the Work Recognition certificate. It **reuses only
pure low-level primitives** from ``modules.certificates.pdf`` (palette, page
geometry, font resolution, tracked-text drawing, QR generation, hashing) and
never calls ``render_certificate_pdf`` — so the two credentials stay visually
coherent yet fully independent.

The QR code encodes the FULL public verification URL
(``.../verify-activity-certificate/<id>``) so a scan lands on the live page.
"""

from __future__ import annotations

import io
import secrets

from reportlab.lib.colors import white
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.utils import ImageReader
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfgen import canvas

from app.models.activity_certificate import (
    ACTIVITY_CERTIFICATE_ID_ALPHABET,
    ACTIVITY_CERTIFICATE_ID_PREFIX,
    ACTIVITY_CERTIFICATE_ID_RANDOM_LENGTH,
    ACTIVITY_CERTIFICATE_SCOPE_STATEMENT,
)
from app.modules.certificates.pdf import (
    CHARCOAL,
    CONTENT_LEFT,
    DIVIDER_X,
    GOLD,
    GOLD_FINE,
    MAIN_WIDTH,
    MUTED,
    _brand_wordmark,
    _draw_background,
    _draw_brand_lockup,
    _draw_calendar_icon,
    _draw_corner_linework,
    _draw_frame,
    _draw_tracked,
    _fit_size,
    _resolve_fonts,
    _safe,
    _wrap,
)

_ACTIVITY_TYPE_LABELS = {
    "project": "Project",
    "programme": "Programme",
    "hackathon": "Hackathon",
}


def generate_activity_certificate_id(year: int) -> str:
    """`THL-ACT-CERT-<year>-<12 random unambiguous chars>` (~60 bits)."""
    suffix = "".join(
        secrets.choice(ACTIVITY_CERTIFICATE_ID_ALPHABET)
        for _ in range(ACTIVITY_CERTIFICATE_ID_RANDOM_LENGTH)
    )
    return f"{ACTIVITY_CERTIFICATE_ID_PREFIX}-{year}-{suffix}"


def build_activity_verification_url(base_url: str, certificate_id: str) -> str:
    return f"{base_url.rstrip('/')}/verify-activity-certificate/{certificate_id}"


def activity_type_label(value: str) -> str:
    return _ACTIVITY_TYPE_LABELS.get(value, value.replace("_", " ").title())


def render_activity_certificate_pdf(
    *,
    certificate_id: str,
    member_name: str,
    activity_title: str,
    activity_type: str,
    award_label: str,
    award_statement: str,
    work_title: str | None,
    issued_at,
    verification_url: str,
    qr_png: bytes,
    template: dict | None = None,
    brand_name: str = "Thridha Labs",
    logo_png: bytes | None = None,
) -> bytes:
    template = template or {}
    heading_text = template.get("heading") or "Certificate of Achievement"
    presentation_line = template.get("presentation_line") or "This certificate is presented to"
    award_line = template.get("award_line") or "in recognition of verified participation as"
    footer_note = template.get("footer_note") or "Activity participation ceremony"
    scope_statement = template.get("scope_statement") or ACTIVITY_CERTIFICATE_SCOPE_STATEMENT

    fonts = _resolve_fonts()
    sans, sans_bold = fonts["sans"], fonts["sans_bold"]
    serif, serif_bold = fonts["serif"], fonts["serif_bold"]
    mono = fonts["mono"]
    wordmark_font = fonts["times_bold"]

    page = landscape(A4)
    width, height = page

    buffer = io.BytesIO()
    c = canvas.Canvas(buffer, pagesize=page)
    c.setTitle(f"Thridha Labs Activity Certificate {certificate_id}")
    c.setAuthor(brand_name or "Thridha Labs")
    c.setSubject("Activity Certificate")
    c.setCreator(brand_name or "Thridha Labs")

    _draw_background(c, width, height)
    _draw_frame(c, width, height)
    _draw_corner_linework(c, width, height)

    _draw_brand_lockup(
        c, brand_name=brand_name, logo_png=logo_png, wordmark_font=wordmark_font
    )

    # ---- Heading -----------------------------------------------------------
    heading_size = _fit_size(heading_text, serif_bold, 31.0, MAIN_WIDTH, 20.0)
    c.setFillColor(CHARCOAL)
    c.setFont(serif_bold, heading_size)
    c.drawString(CONTENT_LEFT, 428, _safe(heading_text, serif_bold))

    # ---- Recipient ---------------------------------------------------------
    c.setFillColor(MUTED)
    c.setFont(sans, 12.5)
    c.drawString(CONTENT_LEFT, 388, _safe(presentation_line, sans))

    name_text = _safe(member_name, serif_bold)
    name_size = _fit_size(name_text, serif_bold, 27.0, MAIN_WIDTH, 18.0)
    if pdfmetrics.stringWidth(name_text, serif_bold, name_size) <= MAIN_WIDTH:
        name_lines = [name_text]
    else:
        name_lines = _wrap(name_text, serif_bold, name_size, MAIN_WIDTH)
    name_y = 344.0
    c.setFillColor(CHARCOAL)
    c.setFont(serif_bold, name_size)
    for line in name_lines:
        c.drawString(CONTENT_LEFT, name_y, line)
        name_y -= name_size * 1.05
    name_bottom = name_y + name_size * 0.04

    divider_y = name_bottom - 22
    c.setStrokeColor(GOLD)
    c.setLineWidth(1.3)
    c.line(CONTENT_LEFT, divider_y, CONTENT_LEFT + 280, divider_y)

    # ---- Award line + label ------------------------------------------------
    c.setFillColor(MUTED)
    c.setFont(sans, 12.5)
    c.drawString(CONTENT_LEFT, divider_y - 26, _safe(award_line, sans))

    label_text = _safe(award_label, serif_bold)
    label_size = _fit_size(label_text, serif_bold, 26.0, MAIN_WIDTH, 15.0)
    c.setFillColor(GOLD)
    c.setFont(serif_bold, label_size)
    label_y = divider_y - 60
    c.drawString(CONTENT_LEFT, label_y, label_text)

    # ---- Statement ---------------------------------------------------------
    y = label_y - 26
    if award_statement:
        statement_size = 11.5
        lines = _wrap(_safe(award_statement, sans), sans, statement_size, MAIN_WIDTH)
        c.setFillColor(MUTED)
        c.setFont(sans, statement_size)
        for line in lines:
            c.drawString(CONTENT_LEFT, y, line)
            y -= statement_size * 1.3

    # ---- Activity title ----------------------------------------------------
    y -= 10
    descriptor = f"{activity_type_label(activity_type)} - {activity_title}"
    activity_size = _fit_size(descriptor, sans_bold, 14.0, MAIN_WIDTH, 11.0)
    activity_lines = _wrap(_safe(descriptor, sans_bold), sans_bold, activity_size, MAIN_WIDTH)
    c.setFillColor(CHARCOAL)
    c.setFont(sans_bold, activity_size)
    for line in activity_lines:
        c.drawString(CONTENT_LEFT, y, line)
        y -= activity_size * 1.28

    # ---- Optional recognized work -----------------------------------------
    if work_title:
        y -= 8
        work_line = f"Recognised work: {work_title}"
        work_size = _fit_size(work_line, sans, 11.0, MAIN_WIDTH, 9.0)
        work_lines = _wrap(_safe(work_line, sans), sans, work_size, MAIN_WIDTH)
        c.setFillColor(MUTED)
        c.setFont(sans, work_size)
        for line in work_lines:
            c.drawString(CONTENT_LEFT, y, line)
            y -= work_size * 1.3

    # ---- Verification column ----------------------------------------------
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

    _draw_footer(c, width, sans, sans_bold, brand_name, footer_note)
    _draw_scope_note(c, width, sans, scope_statement)

    c.showPage()
    c.save()
    data = buffer.getvalue()
    buffer.close()
    return data


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
    right = width - 76.0
    center = (DIVIDER_X + 28.0 + right) / 2

    c.setStrokeColor(GOLD_FINE)
    c.setLineWidth(0.8)
    divider_top = 440.0
    divider_bottom = 92.0
    c.line(DIVIDER_X, divider_bottom, DIVIDER_X, divider_top)
    c.circle(DIVIDER_X, divider_top, 4.4, stroke=1, fill=0)
    c.setFillColor(GOLD)
    c.circle(DIVIDER_X, divider_top, 2.4, stroke=0, fill=1)

    qr_size = 78.0
    pad = 7.0
    qr_top = 430.0
    qr_x = center - qr_size / 2
    qr_y = qr_top - qr_size
    c.setFillColor(white)
    c.setStrokeColor(GOLD_FINE)
    c.setLineWidth(0.7)
    c.roundRect(
        qr_x - pad, qr_y - pad, qr_size + 2 * pad, qr_size + 2 * pad, 3, stroke=1, fill=1
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

    _draw_tracked(
        c,
        center,
        qr_y - 26,
        "Verify Activity Certificate",
        font=sans_bold,
        size=9.0,
        color=CHARCOAL,
        tracking=1.0,
        align="center",
    )

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
    col_width = right - (DIVIDER_X + 28.0)
    id_font_size = _fit_size(certificate_id, mono, 8.0, col_width, 0.0)
    id_lines = _wrap(certificate_id, mono, id_font_size, col_width)
    id_y = id_label_y - 15
    c.setFillColor(CHARCOAL)
    c.setFont(mono, id_font_size)
    for line in id_lines:
        c.drawCentredString(center, id_y, _safe(line, mono))
        id_y -= id_font_size * 1.3


def _draw_footer(
    c: canvas.Canvas,
    width: float,
    sans: str,
    sans_bold: str,
    brand_name: str,
    footer_note: str,
) -> None:
    right = width - 76.0
    c.setStrokeColor(GOLD_FINE)
    c.setLineWidth(0.6)
    c.line(CONTENT_LEFT, 68.0, right, 68.0)
    _draw_tracked(
        c,
        CONTENT_LEFT,
        50.0,
        _safe(footer_note.upper(), sans),
        font=sans,
        size=8,
        color=MUTED,
        tracking=1.4,
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
