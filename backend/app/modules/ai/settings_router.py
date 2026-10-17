"""Admin AI settings API (`/admin/ai/settings`).

Restricted to admin-level roles (`require_role("admin")` → admins/owners;
editors are rejected). The stored Groq key is never returned; only a masked
indicator and metadata are exposed. All mutations require the admin CSRF header.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends

from app.deps.auth import require_role
from app.deps.csrf import require_csrf
from app.models.admin import Admin
from app.modules.ai import settings_service as service
from app.modules.ai.settings_schemas import (
    AiConnectionTestRequest,
    AiConnectionTestResponse,
    AiSettingsResponse,
    AiSettingsUpdate,
)

router = APIRouter(prefix="/admin/ai/settings", tags=["admin-ai-settings"])

_ERROR_RESPONSES = {
    401: {"description": "Authentication required"},
    403: {"description": "Insufficient role (admin/owner required) or CSRF failure"},
    409: {"description": "Encryption not configured or no key stored"},
    422: {"description": "Validation failure"},
}


@router.get(
    "",
    response_model=AiSettingsResponse,
    responses=_ERROR_RESPONSES,
    summary="Get AI settings status (never returns the key)",
)
async def get_ai_settings(
    admin: Admin = Depends(require_role("admin")),
) -> AiSettingsResponse:
    return await service.status_response(admin)


@router.put(
    "",
    response_model=AiSettingsResponse,
    dependencies=[Depends(require_csrf)],
    responses=_ERROR_RESPONSES,
    summary="Set/replace the Groq key and/or update model + enabled flag",
)
async def put_ai_settings(
    payload: AiSettingsUpdate,
    admin: Admin = Depends(require_role("admin")),
) -> AiSettingsResponse:
    await service.update_settings(admin, payload)
    return await service.status_response(admin)


@router.delete(
    "/key",
    response_model=AiSettingsResponse,
    dependencies=[Depends(require_csrf)],
    responses=_ERROR_RESPONSES,
    summary="Remove the stored Groq key",
)
async def delete_ai_key(
    admin: Admin = Depends(require_role("admin")),
) -> AiSettingsResponse:
    await service.remove_key()
    return await service.status_response(admin)


@router.post(
    "/test",
    response_model=AiConnectionTestResponse,
    dependencies=[Depends(require_csrf)],
    responses=_ERROR_RESPONSES,
    summary="Test a proposed or the stored Groq key (never saves a proposed key)",
)
async def test_ai_connection(
    payload: AiConnectionTestRequest,
    admin: Admin = Depends(require_role("admin")),
) -> AiConnectionTestResponse:
    return await service.test_connection(admin, payload)
