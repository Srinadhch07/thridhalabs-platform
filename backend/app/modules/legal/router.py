"""Admin legal documents API."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from app.deps.auth import get_active_admin, require_role
from app.deps.csrf import require_csrf
from app.models.admin import Admin
from app.modules.legal import service
from app.modules.legal.schemas import (
    LegalAdminResponse,
    LegalListResponse,
    LegalPublishRequest,
    LegalSaveDraftRequest,
)

router = APIRouter(prefix="/legal", tags=["legal-admin"])


def _admin(doc) -> LegalAdminResponse:
    return LegalAdminResponse(
        id=doc.id,
        slug=doc.slug,
        title=doc.title,
        content_markdown=doc.content_markdown,
        status=doc.status,
        created_at=doc.created_at,
        updated_at=doc.updated_at,
        published_at=doc.published_at,
    )


@router.get(
    "",
    response_model=LegalListResponse,
    dependencies=[Depends(get_active_admin)],
)
async def list_legal(admin: Admin = Depends(get_active_admin)) -> LegalListResponse:
    items = await service.list_admin()
    return LegalListResponse(items=[_admin(d) for d in items])


@router.get(
    "/{slug}",
    response_model=LegalAdminResponse,
    dependencies=[Depends(get_active_admin)],
)
async def get_legal(slug: str, admin: Admin = Depends(get_active_admin)) -> LegalAdminResponse:
    doc = await service.get_admin(slug)
    return _admin(doc)


@router.put(
    "/{slug}/draft",
    response_model=LegalAdminResponse,
    dependencies=[Depends(require_csrf)],
)
async def save_draft(
    slug: str,
    payload: LegalSaveDraftRequest,
    admin: Admin = Depends(require_role("editor")),
) -> LegalAdminResponse:
    doc = await service.save_draft(
        slug,
        title=payload.title,
        content_markdown=payload.content_markdown,
        expected_updated_at=payload.expected_updated_at,
    )
    return _admin(doc)


@router.post(
    "/{slug}/publish",
    response_model=LegalAdminResponse,
    dependencies=[Depends(require_csrf)],
)
async def publish_legal(
    slug: str,
    payload: LegalPublishRequest,
    admin: Admin = Depends(require_role("editor")),
) -> LegalAdminResponse:
    doc = await service.publish(
        slug,
        title=payload.title,
        content_markdown=payload.content_markdown,
        expected_updated_at=payload.expected_updated_at,
    )
    return _admin(doc)
