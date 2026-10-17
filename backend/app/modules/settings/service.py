"""Settings service — singleton read/update semantics.

- GET never persists: when no document exists a default is returned in memory.
- PUT replaces (absent sections reset to defaults) and creates on first write.
- PATCH merges (only provided fields change) and creates on first write.
The persisted state is produced through the domain model so every stored value
is normalized identically.
"""

from __future__ import annotations

from datetime import datetime, timezone

from app.models.settings import SiteSettings, default_settings_doc
from app.modules.settings import repository
from app.modules.settings.schemas import SettingsUpdate

_SECTION_KEYS = ("general", "contact", "footer", "seo", "analytics")


async def get_settings() -> SiteSettings:
    existing = await repository.get()
    if existing is not None:
        return existing
    # Empty state is returned without persisting anything: a GET must not
    # unexpectedly create data.
    base = default_settings_doc()
    now = datetime.now(timezone.utc)
    return SiteSettings(id="default", created_at=now, updated_at=now, **base)


async def update_settings(payload: SettingsUpdate, *, replace: bool) -> SiteSettings:
    existing = await repository.get()
    if existing is None or replace:
        base = default_settings_doc()
    else:
        base = existing.model_dump(exclude={"id", "created_at", "updated_at"})

    data = payload.model_dump(exclude_unset=True)

    for section in _SECTION_KEYS:
        section_payload = data.get(section)
        if not isinstance(section_payload, dict):
            continue
        for key, value in section_payload.items():
            if value is None:
                continue
            base[section][key] = value

    social = data.get("social")
    if isinstance(social, dict) and isinstance(social.get("urls"), dict):
        for key, value in social["urls"].items():
            if value:
                base["social"]["urls"][key] = value
            else:
                base["social"]["urls"].pop(key, None)

    if "maintenance_mode" in data and data["maintenance_mode"] is not None:
        base["maintenance_mode"] = data["maintenance_mode"]

    now = datetime.now(timezone.utc)
    created_at = existing.created_at if existing is not None else now
    model = SiteSettings(
        id="__ignored__",
        created_at=created_at,
        updated_at=now,
        **base,
    )
    body = model.model_dump(
        exclude={"id", "singleton", "created_at", "updated_at"}
    )
    body["updated_at"] = now
    body["created_at"] = created_at
    return await repository.upsert(body)