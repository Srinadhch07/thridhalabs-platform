"""Public certificate-verification API (`/public/certificates`).

Verifies a certificate by its public id without authentication. Returns only a
safe projection: never the private work content, member email, storage keys,
reviewer identity or internal notes. A random/unknown id 404s identically to a
revoked-but-missing one (existence is not distinguishable via error shape).

Unissued certificates are never reported as valid: the record only ever exists
after a successful issuance, and its `status` is surfaced verbatim.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends

from app.deps.maintenance import require_public_site_available
from app.modules.certificates import service
from app.modules.certificates.schemas import PublicCertificateResponse

router = APIRouter(
    prefix="/public/certificates",
    tags=["public"],
    dependencies=[Depends(require_public_site_available)],
)

_ERROR_RESPONSES = {
    404: {"description": "Certificate not found"},
}


@router.get(
    "/{certificate_id}",
    response_model=PublicCertificateResponse,
    responses=_ERROR_RESPONSES,
    summary="Verify a certificate by its public id",
)
async def verify_certificate(certificate_id: str) -> PublicCertificateResponse:
    data = await service.get_public(certificate_id)
    return PublicCertificateResponse(**data)
