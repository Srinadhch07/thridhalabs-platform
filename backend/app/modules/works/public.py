"""Public work-showcase API — published, public-visible works only.

A work is reachable here only when its owner is active with a public profile
AND the work is published AND its own visibility is `public`. Anything else
404s (existence is never leaked). Internal Mongo ids are not exposed; media is
referenced by id and resolved through the public media route by the frontend.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends

from app.deps.maintenance import require_public_site_available
from app.models.member import Member
from app.models.project import ProjectType
from app.modules.members import service as members_service
from app.modules.works import service
from app.modules.works.schemas import (
    FeaturedContributionAuthor,
    FeaturedContributionCard,
    FeaturedContributionList,
    WorkPublicAuthor,
    WorkPublicResponse,
)

router = APIRouter(
    prefix="/public/members",
    tags=["public"],
    dependencies=[Depends(require_public_site_available)],
)

contributions_router = APIRouter(
    prefix="/public/contributions",
    tags=["public"],
    dependencies=[Depends(require_public_site_available)],
)


def _author(owner: Member) -> WorkPublicAuthor:
    return WorkPublicAuthor(
        member_id=owner.member_id,
        display_name=owner.profile.display_name or owner.full_name or owner.member_id,
        picture_media_id=owner.profile.picture_media_id,
    )


@router.get(
    "/{member_id}/works/{slug}",
    response_model=WorkPublicResponse,
    summary="Get a published public work by member + slug",
)
async def get_public_work(member_id: str, slug: str) -> WorkPublicResponse:
    owner = await members_service.get_public_member(member_id)
    work = await service.get_public_work(owner, slug)
    return WorkPublicResponse(
        slug=work.slug,
        title=work.title,
        summary=work.summary,
        cover_media_id=work.cover_media_id,
        tags=work.tags,
        external_links=work.external_links,
        content=work.content,
        author=_author(owner),
        published_at=work.published_at or work.updated_at,
        updated_at=work.updated_at,
    )


@contributions_router.get(
    "",
    response_model=FeaturedContributionList,
    summary="List featured member contributions (official Projects page)",
)
async def list_featured_contributions() -> FeaturedContributionList:
    pairs = await service.list_featured_contributions()
    items: list[FeaturedContributionCard] = []
    for work, owner in pairs:
        items.append(
            FeaturedContributionCard(
                slug=work.slug,
                title=work.title,
                summary=work.summary,
                cover_media_id=work.cover_media_id,
                tags=work.tags,
                classification=(
                    work.featured_classification or ProjectType.MEMBER_CONTRIBUTION
                ),
                featured_at=work.featured_at,
                published_at=work.published_at,
                author=FeaturedContributionAuthor(
                    member_id=owner.member_id,
                    display_name=(
                        owner.profile.display_name
                        or owner.full_name
                        or owner.member_id
                    ),
                    picture_media_id=owner.profile.picture_media_id,
                ),
            )
        )
    return FeaturedContributionList(items=items)
