"""Public member-profile API — active members with a public profile only.

A profile is reachable only when the member is active AND their
`profile_visibility` is `public`; otherwise it 404s. The profile lists only the
member's published, public-visible works (their own visibility rule still
applies), plus their published, Admin-reviewed AI contribution summaries
(Verified Contributions). Internal Mongo ids, review notes and private fields
are never exposed.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel, ConfigDict

from app.deps.maintenance import require_public_site_available
from app.models.member import Member
from app.modules.ai import service as ai_service
from app.modules.ai.schemas import PublicContributionSummary
from app.modules.members import service as members_service
from app.modules.works import service as works_service
from app.modules.works.schemas import WorkPublicCard

router = APIRouter(
    prefix="/public/members",
    tags=["public"],
    dependencies=[Depends(require_public_site_available)],
)


class MemberPublicProfileResponse(BaseModel):
    """Public projection of a member profile. `member_id` here is the readable
    THL-M-… id, never the internal Mongo `_id`."""

    model_config = ConfigDict(extra="forbid")

    member_id: str
    display_name: str
    bio: str | None
    skills: list[str]
    interests: list[str]
    github_url: str | None
    linkedin_url: str | None
    portfolio_url: str | None
    location: str | None
    picture_media_id: str | None
    works: list[WorkPublicCard]
    contributions: list[PublicContributionSummary]


async def _to_public(member: Member) -> MemberPublicProfileResponse:
    works = await works_service.list_public_works_for_owner(member)
    contributions = await ai_service.list_public_contributions(member)
    return MemberPublicProfileResponse(
        member_id=member.member_id,
        display_name=member.profile.display_name or member.full_name or member.member_id,
        bio=member.profile.bio,
        skills=member.profile.skills,
        interests=member.profile.interests,
        github_url=member.profile.github_url,
        linkedin_url=member.profile.linkedin_url,
        portfolio_url=member.profile.portfolio_url,
        location=member.profile.location,
        picture_media_id=member.profile.picture_media_id,
        works=[
            WorkPublicCard(
                slug=work.slug,
                title=work.title,
                summary=work.summary,
                cover_media_id=work.cover_media_id,
                tags=work.tags,
                published_at=work.published_at or work.updated_at,
            )
            for work in works
        ],
        contributions=contributions,
    )


@router.get(
    "/{member_id}",
    response_model=MemberPublicProfileResponse,
    summary="Get a public member profile and their published public works",
)
async def get_public_profile(member_id: str) -> MemberPublicProfileResponse:
    member = await members_service.get_public_member(member_id)
    return await _to_public(member)
