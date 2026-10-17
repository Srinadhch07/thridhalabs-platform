"""Image content-detection + Pillow processing pipeline tests.

Combines magic-byte detection, decode integrity checks, EXIF stripping,
orientation normalization, variant generation, aspect-ratio preservation, and
no-upscaling guarantees. No HTTP/database involved.
"""

from __future__ import annotations

import hashlib
import io
import struct
import zlib

import pytest
from PIL import Image

from app.core.config import get_settings
from app.modules.media.processing import (
    MIME_BY_FORMAT,
    VARIANT_NAMES,
    ImageTooLargeError,
    InvalidImageError,
    detect_image_format,
    process_image,
    sha256_checksum,
)

TEXT_BYTES = b"This is definitely not an image " * 40


def _jpeg(size=(64, 48), color="red", exif=None) -> bytes:
    buf = io.BytesIO()
    kwargs = {"exif": exif} if exif is not None else {}
    Image.new("RGB", size, color).save(buf, "JPEG", **kwargs)
    return buf.getvalue()


def _png(size=(64, 48), color="red", rgba=False) -> bytes:
    buf = io.BytesIO()
    img = Image.new("RGBA" if rgba else "RGB", size, color)
    img.save(buf, "PNG")
    return buf.getvalue()


def _webp(size=(64, 48), color="red") -> bytes:
    buf = io.BytesIO()
    Image.new("RGB", size, color).save(buf, "WEBP")
    return buf.getvalue()


def _huge_png(width: int, height: int) -> bytes:
    """Minimal, CRC-valid PNG whose header declares enormous dimensions (decompression bomb)."""
    sig = b"\x89PNG\r\n\x1a\n"

    def _chunk(typ: bytes, payload: bytes) -> bytes:
        return (
            struct.pack(">I", len(payload))
            + typ
            + payload
            + struct.pack(">I", zlib.crc32(typ + payload) & 0xFFFFFFFF)
        )

    ihdr = _chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0))
    iend = _chunk(b"IEND", b"")
    return sig + ihdr + iend


@pytest.fixture(scope="module")
def settings():
    return get_settings()


# --------------------------------------------------------------------------
# Content detection
# --------------------------------------------------------------------------
def test_detect_jpeg(): assert detect_image_format(_jpeg()) == "jpeg"
def test_detect_png(): assert detect_image_format(_png()) == "png"
def test_detect_webp(): assert detect_image_format(_webp()) == "webp"


def test_detect_rejects_text():
    assert detect_image_format(TEXT_BYTES) is None


def test_detect_rejects_gif():
    assert detect_image_format(b"GIF89a" + b"\x00" * 64) is None


def test_detect_rejects_short_and_empty():
    assert detect_image_format(b"") is None
    assert detect_image_format(b"\xff\xd8\xff") is None
    assert detect_image_format(None) is None


# --------------------------------------------------------------------------
# Processing
# --------------------------------------------------------------------------
@pytest.mark.parametrize("factory", [_jpeg, _png, _webp])
def test_each_supported_format_processes(factory, settings):
    processed = process_image(factory(), settings)
    assert processed.format in ("jpeg", "png", "webp")
    assert processed.mime_type == MIME_BY_FORMAT[processed.format]
    names = [v.name for v in processed.variants]
    assert names == list(VARIANT_NAMES)
    for variant in processed.variants:
        assert variant.data[:4] == b"RIFF"
        assert variant.data[8:12] == b"WEBP"
        assert variant.mime_type == "image/webp"
        assert variant.size_bytes == len(variant.data)
        assert variant.width > 0 and variant.height > 0


def test_renamed_text_is_rejected(settings):
    with pytest.raises(InvalidImageError):
        process_image(TEXT_BYTES, settings)


def test_truncated_jpeg_is_rejected(settings):
    corrupt = _jpeg(size=(800, 600))[:60]
    with pytest.raises(InvalidImageError):
        process_image(corrupt, settings)


def test_corrupt_png_is_rejected(settings):
    data = _png(size=(800, 600))
    corrupted = data[: len(data) // 2]  # truncated mid-deflate-stream
    with pytest.raises(InvalidImageError):
        process_image(corrupted, settings)


def test_exif_metadata_is_stripped(settings):
    exif = Image.Exif()
    exif[0x010E] = "Secret camera description"
    exif[0x0132] = "2024:01:01 00:00:00"
    source = _jpeg(exif=exif.tobytes())
    assert b"Secret camera description" in source  # source really carries it
    processed = process_image(source, settings)
    for variant in processed.variants:
        assert b"Secret camera description" not in variant.data
        img = Image.open(io.BytesIO(variant.data))
        assert len(img.getexif()) == 0
        assert b"Exif" not in variant.data
        assert img.info.get("exif") is None


def test_exif_orientation_is_normalized(settings):
    exif = Image.Exif()
    exif[0x0112] = 6  # Orientation 6 = rotate 90° CW to display
    processed = process_image(_jpeg(size=(48, 80), exif=exif.tobytes()), settings)
    assert (processed.width, processed.height) == (80, 48)
    original = next(v for v in processed.variants if v.name == "original")
    assert (original.width, original.height) == (80, 48)


def test_variants_preserve_aspect_ratio(settings):
    processed = process_image(_jpeg(size=(3000, 1500)), settings)
    by_name = {v.name: v for v in processed.variants}
    assert (by_name["original"].width, by_name["original"].height) == (3000, 1500)
    assert by_name["md"].width == 1024
    assert by_name["md"].height == 512
    assert by_name["lg"].width == 1920
    assert by_name["lg"].height == 960
    assert by_name["thumb"].width == 256
    assert by_name["thumb"].height == 128
    # aspect ratio 2:1 preserved everywhere
    for v in processed.variants:
        assert round(v.width / v.height, 6) == pytest.approx(2.0)


def test_small_images_are_not_upscaled(settings):
    processed = process_image(_jpeg(size=(100, 50)), settings)
    for variant in processed.variants:
        assert variant.width == 100
        assert variant.height == 50


def test_checksum_is_sha256():
    data = b"payload-bytes"
    assert sha256_checksum(data) == hashlib.sha256(data).hexdigest()


def test_png_alpha_is_preserved(settings):
    processed = process_image(_png(size=(40, 40), color=(0, 0, 0, 0), rgba=True), settings)
    assert processed.has_alpha


def test_decompression_bomb_is_rejected(settings):
    with pytest.raises(ImageTooLargeError):
        process_image(_huge_png(50000, 50000), settings)


def test_width_height_detected_for_png(settings):
    processed = process_image(_png(size=(1234, 567)), settings)
    assert processed.width == 1234
    assert processed.height == 567