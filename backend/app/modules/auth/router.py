"""Authentication endpoints: CSRF bootstrap, login, logout, current account."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Request, Response

from app.deps.auth import get_active_admin
from app.deps.csrf import require_csrf
from app.models.admin import Admin
from app.modules.auth import service
from app.modules.auth.schemas import (
    CsrfResponse,
    LoginRequest,
    MeResponse,
    StatusResponse,
)

router = APIRouter(prefix="/auth", tags=["auth"])

_ERROR_RESPONSES = {
    401: {"description": "Invalid credentials or invalid/expired session"},
    403: {"description": "CSRF failure or disabled account"},
    429: {"description": "Too many login attempts"},
}


@router.get("/csrf", response_model=CsrfResponse, summary="Issue a CSRF token")
async def get_csrf(response: Response) -> CsrfResponse:
    """Bootstrap endpoint: sets the readable CSRF cookie required by every
    state-changing request (including login)."""
    token = service.issue_csrf(response)
    return CsrfResponse(csrfToken=token)


@router.post(
    "/login",
    response_model=StatusResponse,
    dependencies=[Depends(require_csrf)],
    responses=_ERROR_RESPONSES,
    summary="Admin login",
)
async def login(
    payload: LoginRequest,
    request: Request,
    response: Response,
) -> StatusResponse:
    await service.perform_login(request, response, payload)
    return StatusResponse()


@router.post(
    "/logout",
    response_model=StatusResponse,
    dependencies=[Depends(require_csrf)],
    responses=_ERROR_RESPONSES,
    summary="Admin logout (revokes the session)",
)
async def logout(
    response: Response,
    admin: Admin = Depends(get_active_admin),
) -> StatusResponse:
    await service.perform_logout(response, admin)
    return StatusResponse()


@router.get(
    "/me",
    response_model=MeResponse,
    responses=_ERROR_RESPONSES,
    summary="Current authenticated admin",
)
async def me(admin: Admin = Depends(get_active_admin)) -> MeResponse:
    return MeResponse(
        id=admin.id,
        email=admin.email,
        role=admin.role,
        is_active=admin.is_active,
    )
