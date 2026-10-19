"""Pure certificate-PDF layout regression tests.

These drive ``render_certificate_pdf`` directly (no HTTP/DB). They guard the
layout invariants that are easy to regress: a single landscape page carrying the
frozen fields, the deliberate absence of any signature language, a wrapped
fine-print disclaimer, and — most importantly — that decorative letter-spacing
(``Tc``) set on tracked text never leaks into later plain text runs. A previous
regression let that ``Tc`` escape its text object, inflating real glyph widths
until the disclaimer overflowed the frame and off the page.
"""

from __future__ import annotations

import datetime
import io
import re

import pypdf

from app.models.certificate import CERTIFICATE_SCOPE_STATEMENT
from app.modules.certificates import pdf as cert_pdf

CERT_ID = "THL-CERT-2026-ABCDEFGHJKLM"
VERIFY_BASE = "https://thridhalabs.test"


def _render(*, name: str = "Srinath Reddy", title: str = "A Short Title",
            cert_id: str = CERT_ID) -> bytes:
    url = cert_pdf.build_verification_url(VERIFY_BASE, cert_id)
    return cert_pdf.render_certificate_pdf(
        certificate_id=cert_id,
        member_name=name,
        work_title=title,
        issued_at=datetime.datetime(2026, 10, 13, 12, 0, 0),
        verification_url=url,
        qr_png=cert_pdf.generate_qr_png(url),
        brand_name="Thridha Labs",
        logo_png=None,
    )


def _content_stream(pdf_bytes: bytes) -> str:
    return (
        pypdf.PdfReader(io.BytesIO(pdf_bytes))
        .pages[0]
        .get_contents()
        .get_data()
        .decode("latin-1")
    )


def test_pdf_is_single_landscape_page_with_frozen_fields():
    reader = pypdf.PdfReader(io.BytesIO(_render()))
    assert len(reader.pages) == 1

    page = reader.pages[0]
    media = page.mediabox
    assert float(media.width) > float(media.height)  # landscape orientation

    text = (page.extract_text() or "").replace("\n", " ")
    assert CERT_ID in text
    assert "Certificate of Recognition" in text


def test_certificate_contains_no_signature_language():
    text = pypdf.PdfReader(io.BytesIO(_render())).pages[0].extract_text().lower()
    for banned in ("signature", "signatory", "seal", "authorized officer"):
        assert banned not in text


def test_character_spacing_never_leaks_into_plain_text():
    stream = re.sub(r"\(.*?\)", "", _content_stream(_render()), flags=re.S).split()

    depth = 0
    tc_depths: list[int] = []
    for token in stream:
        if token == "q":
            depth += 1
        elif token == "Q":
            assert depth > 0, "unbalanced graphics-state restore"
            depth -= 1
        elif token == "Tc":
            tc_depths.append(depth)

    assert depth == 0, "unbalanced save/restore in the content stream"
    assert tc_depths, "expected tracked text to set character spacing"
    assert all(d > 0 for d in tc_depths), (
        f"letter-spacing (Tc) leaked outside a q/Q save-restore: depths={tc_depths}"
    )


def test_scope_disclaimer_wraps_within_the_content_width():
    fonts = cert_pdf._resolve_fonts()
    max_width = cert_pdf.PAGE_WIDTH - 2 * cert_pdf.CONTENT_LEFT
    lines = cert_pdf._wrap(
        cert_pdf._safe(CERTIFICATE_SCOPE_STATEMENT, fonts["sans"]),
        fonts["sans"],
        6.4,
        max_width,
    )
    assert 0 < len(lines) <= 2
    for line in lines:
        assert cert_pdf.pdfmetrics.stringWidth(line, fonts["sans"], 6.4) <= max_width
