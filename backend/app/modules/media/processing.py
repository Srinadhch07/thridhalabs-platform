"""Content-based image validation and the Pillow processing pipeline.

Uploads are only ever trusted after their actual bytes are inspected:
- magic-byte / content detection (filename and Content-Type are ignored)
- Pillow decode (integrity)
- EXIF metadata stripped, orientation normalized
- transcoded to WebP and resized into responsive variants (never upscaled)

Explicitly NOT supported: GIF (animation), SVG (XML), HEIC/AVIF, PDFs and
arbitrary file uploads. Only JPEG, PNG and WebP are accepted.
"""

from __future__ import annotations

import hashlib
import io
from dataclasses import dataclass

from PIL import Image, ImageOps, UnidentifiedImageError

from app.core.config import Settings

SUPPORTED_FORMATS = ("jpeg", "png", "webp")
MIME_BY_FORMAT = {"jpeg": "image/jpeg", "png": "image/png", "webp": "image/webp"}
STORED_MIME = "image/webp"

VARIANT_NAMES = ("original", "thumb", "md", "lg")
WEBP_QUALITY = 82

_JPEG_MARKER = b"\xff\xd8\xff"
_PNG_MARKER = b"\x89PNG\r\n\x1a\n"
_RIFF_MARKER = b"RIFF"
_WEBP_MAGIC = b"WEBP"


class ImageProcessingError(Exception):
    """Base error for the processing pipeline."""


class InvalidImageError(ImageProcessingError):
    """Bytes are not a decodable JPEG/PNG/WebP image (corrupt/renamed)."""


class ImageTooLargeError(ImageProcessingError):
    """Image exceeds the configured pixel-count safety limit."""


@dataclass(frozen=True)
class VariantOutput:
    name: str
    data: bytes
    width: int
    height: int
    size_bytes: int
    mime_type: str = STORED_MIME


@dataclass(frozen=True)
class ProcessedImage:
    format: str  # detected source format ("jpeg" | "png" | "webp")
    mime_type: str  # detected source MIME
    width: int  # normalized (orientation-fixed, metadata-stripped) dimensions
    height: int
    has_alpha: bool
    variants: tuple[VariantOutput, ...]


def detect_image_format(data: bytes) -> str | None:
    """Identify the image format from the file's actual bytes.

    Returns one of `SUPPORTED_FORMATS` or None for anything unrecognised —
    regardless of filename extension or declared Content-Type.
    """
    if not isinstance(data, bytes) or len(data) < 12:
        return None
    if data[:3] == _JPEG_MARKER:
        return "jpeg"
    if data[:8] == _PNG_MARKER:
        return "png"
    if data[:4] == _RIFF_MARKER and data[8:12] == _WEBP_MAGIC:
        return "webp"
    return None


def sha256_checksum(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def process_image(data: bytes, settings: Settings) -> ProcessedImage:
    """Validate and process image bytes into normalized WebP variants.

    Raises:
        InvalidImageError — not an image or corrupt/undecodable
        ImageTooLargeError — pixel count exceeds MEDIA_MAX_IMAGE_PIXELS
    """
    if detect_image_format(data) is None:
        raise InvalidImageError("Unrecognised image content (expected JPEG, PNG or WebP)")

    # Hard pixel-count ceiling: decompression-bomb guard. Applied before any
    # decode work so crafted huge-dimension headers are rejected early.
    Image.MAX_IMAGE_PIXELS = settings.MEDIA_MAX_IMAGE_PIXELS

    try:
        with Image.open(io.BytesIO(data)) as probe:
            probe.load()  # force a full decode to catch truncated/corrupt data
    except Image.DecompressionBombError as exc:
        raise ImageTooLargeError("Image dimensions exceed the safety limit") from exc
    except Image.DecompressionBombWarning as exc:
        raise ImageTooLargeError("Image dimensions exceed the safety limit") from exc
    except (UnidentifiedImageError, OSError, ValueError) as exc:
        raise InvalidImageError("Image is corrupt or could not be decoded") from exc

    try:
        with Image.open(io.BytesIO(data)) as im:
            # Normalize EXIF orientation (rotates raw pixels into display order).
            im = ImageOps.exif_transpose(im)
            im.load()

            if im.width * im.height > settings.MEDIA_MAX_IMAGE_PIXELS:
                raise ImageTooLargeError("Image dimensions exceed the safety limit")

            if im.mode in ("RGBA", "LA", "PA") or (
                im.mode == "P" and "transparency" in im.info
            ):
                im = im.convert("RGBA")
                has_alpha = True
            else:
                im = im.convert("RGB")
                has_alpha = False

            # Drop embedded metadata (EXIF, ICC, comments, thumbnails).
            im.info.clear()

            width, height = im.size
            variants = _build_variants(im, settings, has_alpha)
    except Image.DecompressionBombError as exc:
        raise ImageTooLargeError("Image dimensions exceed the safety limit") from exc
    except ImageTooLargeError:
        raise
    except (UnidentifiedImageError, OSError, ValueError) as exc:
        raise InvalidImageError("Image is corrupt or could not be decoded") from exc

    return ProcessedImage(
        format=detect_image_format(data),
        mime_type=MIME_BY_FORMAT[detect_image_format(data)],
        width=width,
        height=height,
        has_alpha=has_alpha,
        variants=variants,
    )


def _build_variants(
    base: Image.Image, settings: Settings, has_alpha: bool
) -> tuple[VariantOutput, ...]:
    outputs: list[VariantOutput] = []
    outputs.append(_encode("original", base, has_alpha))
    for name, dimension in (
        ("thumb", settings.MEDIA_THUMB_SIZE),
        ("md", settings.MEDIA_MD_SIZE),
        ("lg", settings.MEDIA_LG_SIZE),
    ):
        variant = base.copy()
        # Pillow's thumbnail() preserves aspect ratio and never upscales.
        variant.thumbnail((dimension, dimension), Image.Resampling.LANCZOS)
        outputs.append(_encode(name, variant, has_alpha))
    return tuple(outputs)


def _encode(name: str, img: Image.Image, has_alpha: bool) -> VariantOutput:
    buf = io.BytesIO()
    kwargs: dict = {"format": "WEBP", "method": 4}
    if has_alpha:
        kwargs["lossless"] = True  # preserve transparency
    else:
        kwargs["quality"] = WEBP_QUALITY
    img.save(buf, **kwargs)
    data = buf.getvalue()
    return VariantOutput(
        name=name,
        data=data,
        width=img.width,
        height=img.height,
        size_bytes=len(data),
    )