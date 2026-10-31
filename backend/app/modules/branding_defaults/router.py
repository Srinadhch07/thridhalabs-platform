from __future__ import annotations

from fastapi import APIRouter, Depends, Response

from app.deps.maintenance import require_public_site_available

from . import service

router = APIRouter(
    tags=["branding-defaults"],
    include_in_schema=False,
    dependencies=[Depends(require_public_site_available)],
)


@router.get("/branding/default/logo.png")
async def default_logo() -> Response:
    resp = service.get_default_logo_response()
    if resp is None:
        return Response(status_code=404)
    return resp


@router.get("/branding/default/logo")
async def default_logo_alt() -> Response:
    resp = service.get_default_logo_response()
    if resp is None:
        return Response(status_code=404)
    return resp
