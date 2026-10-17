"""Admin branding API: GET / PUT /branding (singleton)."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from app.deps.auth import get_active_admin, require_role
from app.deps.csrf import require_csrf
from app.models.admin import Admin
from app.modules.branding import service
from app.modules.branding.schemas import (
    BrandingAdminResponse,
    BrandingUpdate,
    admin_response,
)

router = APIRouter(prefix="/branding", tags=["branding"])

_ERROR_RESPONSES = {
    401: {"description": "Authentication required"},
    403: {"description": "CSRF failure, disabled account or insufficient role"},
    400: {"description": "Referenced media does not exist"},
    422: {"description": "Validation failure"},
}


@router.get(
    "",
    response_model=BrandingAdminResponse,
    responses=_ERROR_RESPONSES,
    summary="Get site branding",
)
async def get_branding(admin: Admin = Depends(get_active_admin)) -> BrandingAdminResponse:
    return admin_response(await service.get_branding())


@router.put(
    "",
    response_model=BrandingAdminResponse,
    dependencies=[Depends(require_csrf)],
    responses=_ERROR_RESPONSES,
    summary="Replace site branding (creates the singleton on first write)",
)
async def put_branding(
    payload: BrandingUpdate,
    admin: Admin = Depends(require_role("editor")),
) -> BrandingAdminResponse:
    return admin_response(await service.update_branding(payload, replace=True))