"""Public branding route: safe, unauthenticated presentation data."""

from __future__ import annotations

from fastapi import APIRouter

from app.modules.branding import service
from app.modules.branding.schemas import (
    BrandingPublicResponse,
    public_response,
)

router = APIRouter(prefix="/public/branding", tags=["public"])


@router.get(
    "",
    response_model=BrandingPublicResponse,
    summary="Get public site branding",
)
async def public_branding() -> BrandingPublicResponse:
    return public_response(await service.get_branding())