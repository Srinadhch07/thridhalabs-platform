"""Member activity-certificate API (`/member/activity-certificates`).

A member may list, read and download the activity certificates they own.
Issuance, revocation and delivery live in the admin router.
"""

from __future__ import annotations

from typing import Literal

from fastapi import APIRouter, Depends, Query
from fastapi.responses import Response

from app.core.pagination import MAX_PAGE_SIZE, page_count
from app.deps.member_auth import get_enabled_member
from app.models.member import Member
from app.modules.activity_certificates import service
from app.modules.activity_certificates.schemas import (
    ActivityCertificateMemberResponse,
    MemberActivityCertificateListResponse,
)

router = APIRouter(
    prefix="/member/activity-certificates", tags=["member-activity-certificates"]
)

_ERROR_RESPONSES = {
    401: {"description": "Authentication required"},
    403: {"description": "Disabled account"},
    404: {"description": "Activity certificate not found"},
    422: {"description": "Validation error"},
}


@router.get(
    "",
    response_model=MemberActivityCertificateListResponse,
    responses=_ERROR_RESPONSES,
    summary="List the member's own activity certificates (paginated)",
)
async def list_certificates(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=MAX_PAGE_SIZE),
    status: Literal["issued", "revoked"] | None = Query(None),
    member: Member = Depends(get_enabled_member),
) -> MemberActivityCertificateListResponse:
    certificates, total = await service.list_for_member(
        member, page=page, page_size=page_size, status=status
    )
    return MemberActivityCertificateListResponse(
        items=[ActivityCertificateMemberResponse.from_certificate(c) for c in certificates],
        total=total,
        page=page,
        page_size=page_size,
        pages=page_count(total, page_size),
    )


@router.get(
    "/{certificate_id}",
    response_model=ActivityCertificateMemberResponse,
    responses=_ERROR_RESPONSES,
    summary="Get one of the member's own activity certificates",
)
async def get_certificate(
    certificate_id: str,
    member: Member = Depends(get_enabled_member),
) -> ActivityCertificateMemberResponse:
    certificate = await service.get_for_member(member, certificate_id)
    return ActivityCertificateMemberResponse.from_certificate(certificate)


@router.get(
    "/{certificate_id}/download",
    responses=_ERROR_RESPONSES,
    summary="Download one of the member's own activity certificate PDFs",
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
