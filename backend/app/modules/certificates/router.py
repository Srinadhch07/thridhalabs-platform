"""Member certificate API (`/member/certificates`).

A member may list, view and download certificates issued to *them*. Issuing,
revoking, editing and emailing are admin-only and deliberately absent here.
"""

from __future__ import annotations

from typing import Literal

from fastapi import APIRouter, Depends, Query
from fastapi.responses import Response

from app.core.pagination import MAX_PAGE_SIZE, page_count
from app.deps.member_auth import get_enabled_member
from app.models.member import Member
from app.modules.certificates import service
from app.modules.certificates.schemas import (
    CertificateMemberResponse,
    MemberCertificateListResponse,
)

router = APIRouter(prefix="/member/certificates", tags=["member-certificates"])

_ERROR_RESPONSES = {
    401: {"description": "Authentication required"},
    403: {"description": "Disabled account"},
    404: {"description": "Certificate not found"},
    422: {"description": "Validation error"},
}


@router.get(
    "",
    response_model=MemberCertificateListResponse,
    responses=_ERROR_RESPONSES,
    summary="List the member's own certificates (paginated)",
)
async def list_certificates(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=MAX_PAGE_SIZE),
    status: Literal["issued", "revoked"] | None = Query(None),
    member: Member = Depends(get_enabled_member),
) -> MemberCertificateListResponse:
    certificates, total = await service.list_for_member(
        member, page=page, page_size=page_size, status=status
    )
    return MemberCertificateListResponse(
        items=[CertificateMemberResponse.from_certificate(c) for c in certificates],
        total=total,
        page=page,
        page_size=page_size,
        pages=page_count(total, page_size),
    )


@router.get(
    "/{certificate_id}",
    response_model=CertificateMemberResponse,
    responses=_ERROR_RESPONSES,
    summary="Get one of the member's own certificates",
)
async def get_certificate(
    certificate_id: str,
    member: Member = Depends(get_enabled_member),
) -> CertificateMemberResponse:
    certificate = await service.get_for_member(member, certificate_id)
    return CertificateMemberResponse.from_certificate(certificate)


@router.get(
    "/{certificate_id}/download",
    responses=_ERROR_RESPONSES,
    summary="Download one of the member's own certificate PDFs",
)
async def download_certificate(
    certificate_id: str,
    member: Member = Depends(get_enabled_member),
) -> Response:
    certificate = await service.get_for_member(member, certificate_id)
    data, filename = await service.open_pdf(certificate)
    return Response(
        content=data,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
