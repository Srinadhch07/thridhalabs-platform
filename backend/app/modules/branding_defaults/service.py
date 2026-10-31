from __future__ import annotations

from pathlib import Path

from fastapi import Response

_ASSET_PATH = Path(__file__).resolve().parent.parent.parent / "assets" / "branding" / "thridhalabs_logo.png"
_CACHE = "public, max-age=31536000, immutable"


def get_default_logo_bytes() -> bytes | None:
    try:
        if not _ASSET_PATH.exists():
            return None
        return _ASSET_PATH.read_bytes()
    except Exception:
        return None


def get_default_logo_response() -> Response | None:
    data = get_default_logo_bytes()
    if not data:
        return None
    return Response(
        content=data,
        media_type="image/png",
        headers={"Cache-Control": _CACHE},
    )
