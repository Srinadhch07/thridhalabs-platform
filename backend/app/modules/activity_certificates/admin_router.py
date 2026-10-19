"""Admin activity-certificate API (`/admin/activity-certificates`).

Issuing, bulk issuance, revoking, emailing and editing the template are
restricted to admin-level roles (`require_role("admin")` -> admins + owners;
editors are rejected) and require CSRF. Listing, reading, eligibility and
downloads are available to any active admin/owner.
"""

from __future__ import annotations

from typing import Literal

from fastapi import APIRouter, Depends, Query
from fastapi.responses import Response

from app.core.pagination import MAX_PAGE_SIZE, page_count
from app.deps.auth import get_active_admin, require_role
from app.deps.csrf import require_csrf
from app.models.admin import Admin
from app.modules.activity_certificates import service
from app.modules.activity_certificates.schemas import (
    ActivityCertificateAdminResponse,
    ActivityCertificateAuditResponse,
    ActivityCertificateBulkIssueRequest,
    ActivityCertificateBulkResult,
    ActivityCertificateBulkFailed,
    ActivityCertificateBulkSkipped,
    ActivityCertificateEmailResponse,
    ActivityCertificateEligibleListResponse,
    ActivityCertificateEligibleParticipant,
    ActivityCertificateIssueRequest,
    ActivityCertificateListResponse,
    ActivityCertificateRevokeRequest,
    ActivityCertificateTemplateResponse,
    ActivityCertificateTemplateUpdateRequest,
)

router = APIRouter(prefix="/admin/activity-certificates", tags=["admin-activity-certificates"])

_ERROR_RESPONSES = {
    401: {"description": "Authentication required"},
    403: {"description": "Insufficient role (admin/owner required)"},
    404: {"description": "Certificate, activity, member or work not found"},
    409: {"description": "Not eligible, already issued, or already revoked"},
    422: {"description": "Validation error"},
    502: {"description": "Certificate email delivery failed"},
    503: {"description": "Activity certificate verification URL is not configured"},
}


@router.post(
    "",
    status_code=201,
    response_model=ActivityCertificateAdminResponse,
    dependencies=[Depends(require_csrf)],
    responses=_ERROR_RESPONSES,
    summary="Issue an activity certificate to a confirmed participant",
)
async def issue_certificate(
    payload: ActivityCertificateIssueRequest,
    admin: Admin = Depends(require_role("admin")),
) -> ActivityCertificateAdminResponse:
    certificate = await service.issue_certificate(
        admin, payload, by_role=admin.role.value
    )
    return ActivityCertificateAdminResponse.from_certificate(certificate)


@router.post(
    "/bulk",
    response_model=ActivityCertificateBulkResult,
    dependencies=[Depends(require_csrf)],
    responses=_ERROR_RESPONSES,
    summary="Issue activity certificates to many participants (per-item results)",
)
async def bulk_issue_certificates(
    payload: ActivityCertificateBulkIssueRequest,
    admin: Admin = Depends(require_role("admin")),
) -> ActivityCertificateBulkResult:
    result = await service.issue_bulk(admin, payload, by_role=admin.role.value)
    return ActivityCertificateBulkResult(
        issued=[
            ActivityCertificateAdminResponse.from_certificate(c)
            for c in result["issued"]
        ],
        skipped=[ActivityCertificateBulkSkipped(**item) for item in result["skipped"]],
        failed=[ActivityCertificateBulkFailed(**item) for item in result["failed"]],
        issued_count=result["issued_count"],
        skipped_count=result["skipped_count"],
        failed_count=result["failed_count"],
    )


@router.get(
    "/template",
    response_model=ActivityCertificateTemplateResponse,
    responses=_ERROR_RESPONSES,
    summary="Get the activity certificate template",
)
async def get_template(
    admin: Admin = Depends(get_active_admin),
) -> ActivityCertificateTemplateResponse:
    template = await service.get_or_default_template()
    return ActivityCertificateTemplateResponse.from_template(template)


@router.put(
    "/template",
    response_model=ActivityCertificateTemplateResponse,
    dependencies=[Depends(require_csrf)],
    responses=_ERROR_RESPONSES,
    summary="Update the activity certificate template (admin/owner only)",
)
async def update_template(
    payload: ActivityCertificateTemplateUpdateRequest,
    admin: Admin = Depends(require_role("admin")),
) -> ActivityCertificateTemplateResponse:
    template = await service.update_template(admin, payload)
    return ActivityCertificateTemplateResponse.from_template(template)


@router.get(
    "/eligible",
    response_model=ActivityCertificateEligibleListResponse,
    responses=_ERROR_RESPONSES,
    summary="List confirmed participants eligible for a certificate",
)
async def list_eligible(
    activity_id: str,
    admin: Admin = Depends(get_active_admin),
) -> ActivityCertificateEligibleListResponse:
    data = await service.list_eligible_participants(activity_id)
    return ActivityCertificateEligibleListResponse(
        activity_id=data["activity_id"],
        activity_title=data["activity_title"],
        items=[
            ActivityCertificateEligibleParticipant(**item) for item in data["items"]
        ],
    )


@router.get(
    "",
    response_model=ActivityCertificateListResponse,
    responses=_ERROR_RESPONSES,
    summary="List issued activity certificates (paginated)",
)
async def list_certificates(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=MAX_PAGE_SIZE),
    status: Literal["issued", "revoked"] | None = Query(None),
    activity_id: str | None = Query(None, max_length=64),
    member_id: str | None = Query(None, max_length=64),
    award_category: Literal[
        "first_place", "second_place", "runner_up", "participation", "custom"
    ]
    | None = Query(None),
    admin: Admin = Depends(get_active_admin),
) -> ActivityCertificateListResponse:
    certificates, total = await service.admin_list(
        page=page,
        page_size=page_size,
        status=status,
        activity_id=activity_id,
        member_id=member_id,
        award_category=award_category,
    )
    return ActivityCertificateListResponse(
        items=[
            ActivityCertificateAdminResponse.from_certificate(c) for c in certificates
        ],
        total=total,
        page=page,
        page_size=page_size,
        pages=page_count(total, page_size),
    )


@router.get(
    "/{certificate_id}",
    response_model=ActivityCertificateAdminResponse,
    responses=_ERROR_RESPONSES,
    summary="Get one activity certificate by its public id",
)
async def get_certificate(
    certificate_id: str,
    admin: Admin = Depends(get_active_admin),
) -> ActivityCertificateAdminResponse:
    certificate = await service.admin_get(certificate_id)
    return ActivityCertificateAdminResponse.from_certificate(certificate)


@router.get(
    "/{certificate_id}/download",
    responses=_ERROR_RESPONSES,
    summary="Download the activity certificate PDF",
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


@router.get(
    "/{certificate_id}/audit",
    response_model=list[ActivityCertificateAuditResponse],
    responses=_ERROR_RESPONSES,
    summary="Get the immutable audit history for a certificate",
)
async def get_audit(
    certificate_id: str,
    admin: Admin = Depends(get_active_admin),
) -> list[ActivityCertificateAuditResponse]:
    await service.admin_get(certificate_id)
    entries = await service.list_audit(certificate_id)
    return [ActivityCertificateAuditResponse.from_entry(e) for e in entries]


@router.post(
    "/{certificate_id}/email",
    response_model=ActivityCertificateEmailResponse,
    dependencies=[Depends(require_csrf)],
    responses=_ERROR_RESPONSES,
    summary="Email the activity certificate PDF to the member (admin/owner only)",
)
async def email_certificate(
    certificate_id: str,
    admin: Admin = Depends(require_role("admin")),
) -> ActivityCertificateEmailResponse:
    certificate = await service.send_certificate_email(admin, certificate_id)
    return ActivityCertificateEmailResponse(
        certificate_id=certificate.certificate_id,
        email_status=certificate.email_status,
        email_sent_at=certificate.email_sent_at,
        message="Activity certificate email sent",
    )


@router.post(
    "/{certificate_id}/revoke",
    response_model=ActivityCertificateAdminResponse,
    dependencies=[Depends(require_csrf)],
    responses=_ERROR_RESPONSES,
    summary="Revoke an activity certificate with a mandatory reason (admin/owner only)",
)
async def revoke_certificate(
    certificate_id: str,
    payload: ActivityCertificateRevokeRequest,
    admin: Admin = Depends(require_role("admin")),
) -> ActivityCertificateAdminResponse:
    certificate = await service.revoke_certificate(
        admin, certificate_id, payload.clean_reason(), by_role=admin.role.value
    )
    return ActivityCertificateAdminResponse.from_certificate(certificate)
