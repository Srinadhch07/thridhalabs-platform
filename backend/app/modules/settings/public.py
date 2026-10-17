"""Public settings route: a safe, unauthenticated subset for the public site.

Analytics identifiers and verification tokens are admin-only and are never
exposed here. `maintenance_mode` is public by design — the frontend
maintenance gate reads it to decide whether to show the maintenance page.
"""

from __future__ import annotations

from fastapi import APIRouter

from app.modules.settings import service
from app.modules.settings.schemas import (
    SettingsPublicResponse,
    public_response,
)

router = APIRouter(prefix="/public/settings", tags=["public"])


@router.get(
    "",
    response_model=SettingsPublicResponse,
    summary="Get public site settings",
)
async def public_settings() -> SettingsPublicResponse:
    settings = await service.get_settings()
    return public_response(settings)