"""Admin settings API: GET / PUT / PATCH /settings (singleton)."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from app.deps.auth import get_active_admin, require_role
from app.deps.csrf import require_csrf
from app.models.admin import Admin
from app.modules.settings import service
from app.modules.settings.schemas import (
    SettingsAdminResponse,
    SettingsUpdate,
    admin_response,
)

router = APIRouter(prefix="/settings", tags=["settings"])

_ERROR_RESPONSES = {
    401: {"description": "Authentication required"},
    403: {"description": "CSRF failure, disabled account or insufficient role"},
    422: {"description": "Validation failure"},
}


@router.get(
    "",
    response_model=SettingsAdminResponse,
    responses=_ERROR_RESPONSES,
    summary="Get site settings",
)
async def get_settings(admin: Admin = Depends(get_active_admin)) -> SettingsAdminResponse:
    settings = await service.get_settings()
    return admin_response(settings)


@router.put(
    "",
    response_model=SettingsAdminResponse,
    dependencies=[Depends(require_csrf)],
    responses=_ERROR_RESPONSES,
    summary="Replace site settings (creates the singleton on first write)",
)
async def put_settings(
    payload: SettingsUpdate,
    admin: Admin = Depends(require_role("editor")),
) -> SettingsAdminResponse:
    settings = await service.update_settings(payload, replace=True)
    return admin_response(settings)


@router.patch(
    "",
    response_model=SettingsAdminResponse,
    dependencies=[Depends(require_csrf)],
    responses=_ERROR_RESPONSES,
    summary="Partially update site settings (creates the singleton on first write)",
)
async def patch_settings(
    payload: SettingsUpdate,
    admin: Admin = Depends(require_role("editor")),
) -> SettingsAdminResponse:
    settings = await service.update_settings(payload, replace=False)
    return admin_response(settings)