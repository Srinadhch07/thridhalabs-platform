"""Public legal documents API."""

from __future__ import annotations

from fastapi import APIRouter

from app.modules.legal import service
from app.modules.legal.schemas import LegalPublicResponse

router = APIRouter(prefix="/public/legal", tags=["legal-public"])


@router.get("/{slug}", response_model=LegalPublicResponse)
async def get_public_legal(slug: str) -> LegalPublicResponse:
    doc = await service.get_public(slug)
    return LegalPublicResponse(
        slug=doc.slug,
        title=doc.title,
        content_markdown=doc.content_markdown,
        updated_at=doc.updated_at,
        published_at=doc.published_at,
    )
