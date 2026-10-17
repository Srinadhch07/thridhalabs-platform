"""Member-facing activities API (`/member/activities`).

Members can browse the activities they are involved in plus open
(programme/hackathon) activities they may join, self-register, and withdraw
their own self-registration. Respondent/reply handling for project invitations
is intentionally manual (by email), so no member endpoint changes an
invitation's status — only admins do.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends

from app.deps.csrf import require_member_csrf
from app.deps.member_auth import get_enabled_member
from app.models.member import Member
from app.modules.activities import service
from app.modules.activities.schemas import (
    MemberActivityListResponse,
    MemberActivityResponse,
)

router = APIRouter(prefix="/member/activities", tags=["member-activities"])

_ERROR_RESPONSES = {
    401: {"description": "Authentication required"},
    403: {"description": "CSRF failure, disabled account or invitation-only"},
    404: {"description": "Activity not found"},
    409: {"description": "Already registered or registration closed"},
}


@router.get(
    "",
    response_model=MemberActivityListResponse,
    responses=_ERROR_RESPONSES,
    summary="List my activities and open activities to join",
)
async def list_my_activities(
    member: Member = Depends(get_enabled_member),
) -> MemberActivityListResponse:
    items = await service.list_member_activities(member)
    return MemberActivityListResponse(items=items)


@router.post(
    "/{slug}/register",
    response_model=MemberActivityResponse,
    dependencies=[Depends(require_member_csrf)],
    responses=_ERROR_RESPONSES,
    summary="Self-register for an open activity",
)
async def register(
    slug: str, member: Member = Depends(get_enabled_member)
) -> MemberActivityResponse:
    await service.register(member, slug)
    return await service.get_member_activity(member, slug)


@router.post(
    "/{slug}/withdraw",
    response_model=MemberActivityResponse,
    dependencies=[Depends(require_member_csrf)],
    responses=_ERROR_RESPONSES,
    summary="Withdraw my self-registration",
)
async def withdraw(
    slug: str, member: Member = Depends(get_enabled_member)
) -> MemberActivityResponse:
    await service.withdraw(member, slug)
    return await service.get_member_activity(member, slug)
