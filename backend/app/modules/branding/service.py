"""Branding service — singleton read/update with media reference validation.

Same semantics as settings: GET never persists; PUT replaces (defaults for
absent values) and creates on first write; PATCH merges. Provided media
references are validated against the media collection.
"""

from __future__ import annotations

from datetime import datetime, timezone

from app.models.branding import Branding, default_branding_doc
from app.modules.branding import repository
from app.modules.branding.schemas import BrandingUpdate
from app.services.references import require_media_exist

_MEDIA_KEYS = ("logo", "logo_dark", "logo_light", "favicon", "og_image")


async def get_branding() -> Branding:
    existing = await repository.get()
    if existing is not None:
        return existing
    base = default_branding_doc()
    now = datetime.now(timezone.utc)
    return Branding(id="default", created_at=now, updated_at=now, **base)


async def update_branding(payload: BrandingUpdate, *, replace: bool) -> Branding:
    existing = await repository.get()
    if existing is None or replace:
        base = default_branding_doc()
    else:
        base = existing.model_dump(exclude={"id", "created_at", "updated_at"})

    data = payload.model_dump(exclude_unset=True)

    media_payload = data.get("media")
    if isinstance(media_payload, dict):
        for key in _MEDIA_KEYS:
            if key in media_payload and media_payload[key] is not None:
                base["media"][key] = media_payload[key]
            elif key in media_payload:
                base["media"].pop(key, None)
        await require_media_exist([str(v) for v in media_payload.values() if v])
    elif replace:
        base["media"] = {}

    colors_payload = data.get("colors")
    if isinstance(colors_payload, dict):
        for key, value in colors_payload.items():
            if value is not None:
                base["colors"][key] = value
    elif replace:
        base["colors"] = default_branding_doc()["colors"]

    mode = data.get("mode")
    if mode is not None:
        base["mode"] = mode
    elif replace:
        base["mode"] = "light"

    if "theme_preset" in data:  # explicit null clears the selection too
        base["theme_preset"] = data["theme_preset"]

    now = datetime.now(timezone.utc)
    created_at = existing.created_at if existing is not None else now
    model = Branding(
        id="__ignored__",
        created_at=created_at,
        updated_at=now,
        **base,
    )
    body = model.model_dump(exclude={"id", "singleton", "created_at", "updated_at"})
    body["created_at"] = created_at
    body["updated_at"] = now
    return await repository.upsert(body)