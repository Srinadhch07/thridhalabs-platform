"""Public activity-certificate verification API (`/public/activity-certificates`)."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from app.deps.maintenance import require_public_site_available
from app.modules.activity_certificates import service
from app.modules.activity_certificates.schemas import PublicActivityCertificateResponse

router = APIRouter(
    prefix="/public/activity-certificates",
    tags=["public"],
    dependencies=[Depends(require_public_site_available)],
)

_ERROR_RESPONSES = {
    404: {"description": "Activity certificate not found"},
}


@router.get(
    "/{certificate_id}",
    response_model=PublicActivityCertificateResponse,
    responses=_ERROR_RESPONSES,
    summary="Verify an activity certificate by its public id",
)
async def verify_activity_certificate(
    certificate_id: str,
) -> PublicActivityCertificateResponse:
    data = await service.get_public(certificate_id)
    return PublicActivityCertificateResponse(**data)