"""Admin certificate API (`/admin/certificates`).

Issuing, revoking and emailing certificates are restricted to admin-level roles
(`require_role("admin")` → admins + owners; editors are rejected). Listing,
reading and downloading are available to any active admin/owner.
"""

from __future__ import annotations

from typing import Literal

from fastapi import APIRouter, Depends, Query
from fastapi.responses import Response

from app.core.pagination import MAX_PAGE_SIZE, page_count
from app.deps.auth import get_active_admin, require_role
from app.deps.csrf import require_csrf
from app.models.admin import Admin
from app.modules.certificates import service
from app.modules.certificates.schemas import (
    CertificateAdminResponse,
    CertificateEmailResponse,
    CertificateIssueRequest,
    CertificateListResponse,
    CertificateRevokeRequest,
)

router = APIRouter(prefix="/admin/certificates", tags=["admin-certificates"])

_ERROR_RESPONSES = {
    401: {"description": "Authentication required"},
    403: {"description": "Insufficient role (admin/owner required)"},
    404: {"description": "Certificate or review request not found"},
    409: {"description": "Request not approved, already issued, or already revoked"},
    422: {"description": "Validation error"},
    502: {"description": "Certificate email delivery failed"},
    503: {"description": "Certificate verification URL is not configured"},
}


@router.post(
    "",
    status_code=201,
    response_model=CertificateAdminResponse,
    dependencies=[Depends(require_csrf)],
    responses=_ERROR_RESPONSES,
    summary="Approve (if needed) and issue a certificate for a review request",
)
async def issue_certificate(
    payload: CertificateIssueRequest,
    admin: Admin = Depends(require_role("admin")),
) -> CertificateAdminResponse:
    certificate = await service.issue_certificate(
        admin, payload.request_id, by_role=admin.role.value
    )
    return CertificateAdminResponse.from_certificate(certificate)


@router.get(
    "",
    response_model=CertificateListResponse,
    responses=_ERROR_RESPONSES,
    summary="List issued certificates (paginated)",
)
async def list_certificates(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=MAX_PAGE_SIZE),
    status: Literal["issued", "revoked"] | None = Query(None),
    member_id: str | None = Query(None, max_length=64),
    request_id: str | None = Query(None, max_length=64),
    admin: Admin = Depends(get_active_admin),
) -> CertificateListResponse:
    certificates, total = await service.admin_list(
        page=page,
        page_size=page_size,
        status=status,
        member_id=member_id,
        request_id=request_id,
    )
    return CertificateListResponse(
        items=[CertificateAdminResponse.from_certificate(c) for c in certificates],
        total=total,
        page=page,
        page_size=page_size,
        pages=page_count(total, page_size),
    )


@router.get(
    "/{certificate_id}",
    response_model=CertificateAdminResponse,
    responses=_ERROR_RESPONSES,
    summary="Get one certificate by its public id",
)
async def get_certificate(
    certificate_id: str,
    admin: Admin = Depends(get_active_admin),
) -> CertificateAdminResponse:
    certificate = await service.admin_get(certificate_id)
    return CertificateAdminResponse.from_certificate(certificate)


@router.get(
    "/{certificate_id}/download",
    responses=_ERROR_RESPONSES,
    summary="Download the certificate PDF",
)
async def download_certificate(
    certificate_id: str,
    admin: Admin = Depends(get_active_admin),
) -> Response:
    certificate = await service.admin_get(certificate_id)
    data, filename = await service.open_pdf(certificate)
    return Response(
        content=data,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.post(
    "/{certificate_id}/email",
    response_model=CertificateEmailResponse,
    dependencies=[Depends(require_csrf)],
    responses=_ERROR_RESPONSES,
    summary="Email the certificate PDF to the member (admin/owner only)",
)
async def email_certificate(
    certificate_id: str,
    admin: Admin = Depends(require_role("admin")),
) -> CertificateEmailResponse:
    certificate = await service.send_certificate_email(admin, certificate_id)
    return CertificateEmailResponse(
        certificate_id=certificate.certificate_id,
        email_status=certificate.email_status,
        email_sent_at=certificate.email_sent_at,
        message="Certificate email sent",
    )


@router.post(
    "/{certificate_id}/revoke",
    response_model=CertificateAdminResponse,
    dependencies=[Depends(require_csrf)],
    responses=_ERROR_RESPONSES,
    summary="Revoke a certificate with a mandatory reason (admin/owner only)",
)
async def revoke_certificate(
    certificate_id: str,
    payload: CertificateRevokeRequest,
    admin: Admin = Depends(require_role("admin")),
) -> CertificateAdminResponse:
    certificate = await service.revoke_certificate(
        admin, certificate_id, payload.clean_reason(), by_role=admin.role.value
    )
    return CertificateAdminResponse.from_certificate(certificate)
