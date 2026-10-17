"""Works service: create/update/publish/delete, slug handling, media ownership,
content-document limits, and strict composite public-visibility rules.

Public reachability is derived, never stored:
  published AND visibility == public AND owner active AND profile public.
"""

from __future__ import annotations

from datetime import datetime, timezone

from pymongo.errors import DuplicateKeyError

from app.core.errors import AppError
from app.core.slugs import slugify
from app.models.admin import Admin
from app.models.member import (
    Member,
    MemberStatus,
    ProfileVisibility,
)
from app.models.project import ProjectType
from app.models.work import (
    ContentDocument,
    MAX_BLOCKS,
    MAX_TEXT_TOTAL,
    MemberWork,
    WorkPublicationStatus,
    WorkVisibility,
)
from app.modules.certifications import repository as certifications_repository
from app.modules.members import repository as members_repository
from app.modules.works import repository
from app.modules.works.schemas import (
    WorkCertificationRef,
    WorkCreateRequest,
    WorkUpdateRequest,
)
from app.services.references import require_media_exist

_FALLBACK_SLUG = "work"


async def _unique_slug(member_id: str, title: str) -> str:
    base = slugify(title) or _FALLBACK_SLUG
    candidate = base
    counter = 2
    while await repository.find_by_slug(member_id, candidate) is not None:
        candidate = f"{base}-{counter}"
        counter += 1
    return candidate


async def _validate_owned_media(member_id: str, media_ids: list[str]) -> None:
    """Every referenced media record must exist AND belong to the member."""
    distinct = list(dict.fromkeys(media_id for media_id in media_ids if media_id))
    if not distinct:
        return
    await require_media_exist(distinct)
    from app.modules.media import repository as media_repository

    found = await media_repository.find_many_by_id(distinct)
    for media_id in distinct:
        media = found.get(media_id)
        if media is None or media.created_by != member_id:
            raise AppError(
                422,
                "MEDIA_NOT_OWNED",
                "Referenced media does not exist or is not yours",
            )


def _validate_content(document: ContentDocument) -> None:
    """Aggregate content-document limits (per-block bounds are Pydantic's)."""
    if len(document.blocks) > MAX_BLOCKS:
        raise AppError(422, "CONTENT_TOO_LARGE", f"At most {MAX_BLOCKS} blocks are allowed")
    total = 0
    for block in document.blocks:
        if hasattr(block, "text"):
            total += len(block.text)
        for field_name in ("items", "spans"):
            values = getattr(block, field_name, None)
            if isinstance(values, list):
                for item in values:
                    if isinstance(item, str):
                        total += len(item)
                    elif hasattr(item, "text"):
                        total += len(item.text)
        if hasattr(block, "code"):
            total += len(block.code)
    if total > MAX_TEXT_TOTAL:
        raise AppError(
            422, "CONTENT_TOO_LARGE", "Work content exceeds the total text limit"
        )


async def _get_or_404(work_id: str) -> MemberWork:
    work = await repository.find_by_id(work_id)
    if work is None:
        raise AppError(404, "WORK_NOT_FOUND", "Work was not found")
    return work


async def _owned_or_404(work_id: str, member_id: str) -> MemberWork:
    work = await _get_or_404(work_id)
    if work.member_id != member_id:
        raise AppError(404, "WORK_NOT_FOUND", "Work was not found")
    return work


async def get_certification_ref(work: MemberWork) -> WorkCertificationRef:
    refs = await _certification_refs([work])
    return refs[work.id]


def _is_reviewable(work: MemberWork, request) -> bool:
    if work.publication_status != WorkPublicationStatus.PUBLISHED:
        return False
    return request is None or request.status in ("approved", "rejected", "changes_requested")


async def _certification_refs(
    works: list[MemberWork],
) -> dict[str, WorkCertificationRef]:
    refs: dict[str, WorkCertificationRef] = {}
    by_work = await certifications_repository.find_latest_by_work_ids(
        [work.id for work in works]
    )
    for work in works:
        request = by_work.get(work.id)
        if request is None:
            # No request yet: eligibility still depends on publication state, so
            # a published work must report `reviewable=True` (otherwise the UI
            # cannot tell "not yet requested" apart from "already in review").
            refs[work.id] = WorkCertificationRef(reviewable=_is_reviewable(work, None))
            continue
        changed = (
            request.status in ("approved", "rejected")
            and work.version > request.version_reviewed
        )
        refs[work.id] = WorkCertificationRef(
            request_id=request.id,
            status=request.status,
            version_reviewed=request.version_reviewed,
            reviewed_at=request.decided_at,
            feedback=request.latest_feedback,
            changed_since_review=changed,
            reviewable=_is_reviewable(work, request),
        )
    return refs


# --------------------------------------------------------------------------
# Member CRUD
# --------------------------------------------------------------------------
async def create_work(member: Member, payload: WorkCreateRequest) -> MemberWork:
    content = payload.content
    if content is None:
        template = payload.template or "blank-canvas"
        content = ContentDocument(blocks=ContentDocument.template_blocks(template))
    _validate_content(content)

    media_ids = ([payload.cover_media_id] if payload.cover_media_id else []) + content.media_ids()
    await _validate_owned_media(member.id, media_ids)

    slug = await _unique_slug(member.id, payload.title)
    try:
        return await repository.insert_work(
            member_id=member.id,
            title=payload.title,
            slug=slug,
            summary=payload.summary,
            cover_media_id=payload.cover_media_id,
            tags=payload.tags,
            external_links=payload.external_links,
            content=content,
            visibility=payload.visibility,
            publication_status=WorkPublicationStatus.DRAFT,
            published_at=None,
        )
    except DuplicateKeyError as exc:  # pragma: no cover - unique slug race
        raise AppError(409, "SLUG_TAKEN", "A work with this slug already exists") from exc


async def update_work(
    member: Member, work_id: str, payload: WorkUpdateRequest
) -> MemberWork:
    existing = await _owned_or_404(work_id, member.id)
    data = payload.model_dump(exclude_unset=True)

    # `model_dump` renders the nested ContentDocument as a plain dict, but the
    # service validates the model (exactly as create does). Read the validated
    # model from the request instead of the dumped mapping so `_validate_content`
    # always receives a ContentDocument.
    content: ContentDocument | None = None
    if "content" in data and payload.content is not None:
        content = payload.content
        _validate_content(content)

    media_ids: list[str] = []
    if "cover_media_id" in data and data["cover_media_id"]:
        media_ids.append(data["cover_media_id"])
    if content is not None:
        media_ids.extend(content.media_ids())
    if media_ids:
        await _validate_owned_media(member.id, media_ids)

    fields: dict = {}
    if "title" in data:
        fields["title"] = data["title"]
        fields["slug"] = await _unique_slug(member.id, data["title"])
    if "summary" in data:
        fields["summary"] = data["summary"]
    if "cover_media_id" in data and data["cover_media_id"] is None:
        fields["cover_media_id"] = None
    elif "cover_media_id" in data:
        fields["cover_media_id"] = data["cover_media_id"]
    if "tags" in data:
        fields["tags"] = data["tags"]
    if "external_links" in data:
        fields["external_links"] = data["external_links"]
    if content is not None:
        fields["content"] = content.model_dump()
    if "visibility" in data:
        fields["visibility"] = data["visibility"].value

    if not fields:
        return existing

    updated = await repository.update_work(work_id, fields)
    if updated is None:
        raise AppError(404, "WORK_NOT_FOUND", "Work was not found")
    return updated


async def set_publication(
    member: Member, work_id: str, target: WorkPublicationStatus
) -> MemberWork:
    work = await _owned_or_404(work_id, member.id)
    if work.publication_status == target:
        return work
    fields: dict = {"publication_status": target.value}
    if target == WorkPublicationStatus.PUBLISHED and work.published_at is None:
        fields["published_at"] = datetime.now(timezone.utc)
    updated = await repository.update_work(work_id, fields)
    if updated is None:
        raise AppError(404, "WORK_NOT_FOUND", "Work was not found")
    return updated


async def delete_work(member: Member, work_id: str) -> None:
    work = await _owned_or_404(work_id, member.id)
    active = await certifications_repository.find_active_for_work(work_id)
    if active is not None:
        raise AppError(
            409,
            "CERTIFICATION_IN_PROGRESS",
            "This work has an active certification review and cannot be deleted",
        )
    await repository.delete_by_id(work_id)


async def get_for_member(member: Member, work_id: str) -> MemberWork:
    return await _owned_or_404(work_id, member.id)


async def list_for_member(
    member: Member, *, page: int, page_size: int, status: str | None, sort: list[tuple]
) -> tuple[list[MemberWork], dict[str, WorkCertificationRef], int]:
    query: dict = {"member_id": member.id}
    if status:
        if status not in {item.value for item in WorkPublicationStatus}:
            raise AppError(422, "INVALID_STATUS", "Unknown publication status filter")
        query["publication_status"] = status
    works, total = await repository.list_works(
        query=query, sort=sort, skip=(page - 1) * page_size, limit=page_size
    )
    refs = await _certification_refs(works)
    return works, refs, total


# --------------------------------------------------------------------------
# Publication review (member submission + admin decision) and featuring
# --------------------------------------------------------------------------
_REVIEW_RESUBMITTABLE = {
    WorkPublicationStatus.DRAFT,
    WorkPublicationStatus.CHANGES_REQUESTED,
    WorkPublicationStatus.REJECTED,
    WorkPublicationStatus.UNPUBLISHED,
}


async def submit_for_review(member: Member, work_id: str) -> MemberWork:
    """Submit a work for publication review. Members can never publish here —
    only an admin decision moves a work to `published`."""
    work = await _owned_or_404(work_id, member.id)
    if work.publication_status == WorkPublicationStatus.PENDING_REVIEW:
        raise AppError(
            409, "REVIEW_ALREADY_PENDING", "This work is already awaiting review"
        )
    if work.publication_status == WorkPublicationStatus.PUBLISHED:
        raise AppError(
            409, "WORK_ALREADY_PUBLISHED", "This work is already published"
        )
    fields: dict = {
        "publication_status": WorkPublicationStatus.PENDING_REVIEW.value,
        "submitted_at": datetime.now(timezone.utc),
        "review_feedback": None,
        "reviewed_at": None,
        "reviewed_by": None,
    }
    updated = await repository.update_work(work_id, fields)
    if updated is None:  # pragma: no cover - deleted concurrently
        raise AppError(404, "WORK_NOT_FOUND", "Work was not found")
    return updated


async def withdraw_submission(member: Member, work_id: str) -> MemberWork:
    """Withdraw a pending submission (or a changes-requested work) back to draft."""
    work = await _owned_or_404(work_id, member.id)
    if work.publication_status not in (
        WorkPublicationStatus.PENDING_REVIEW,
        WorkPublicationStatus.CHANGES_REQUESTED,
    ):
        raise AppError(
            409, "NOT_AWAITING_REVIEW", "This work is not awaiting review"
        )
    updated = await repository.update_work(
        work_id,
        {
            "publication_status": WorkPublicationStatus.DRAFT.value,
            "submitted_at": None,
        },
    )
    if updated is None:  # pragma: no cover - deleted concurrently
        raise AppError(404, "WORK_NOT_FOUND", "Work was not found")
    return updated


async def get_for_admin(work_id: str) -> MemberWork:
    work = await repository.find_by_id(work_id)
    if work is None:
        raise AppError(404, "WORK_NOT_FOUND", "Work was not found")
    return work


async def list_for_admin(
    *, page: int, page_size: int, status: str | None, featured: bool | None, sort: list[tuple]
) -> tuple[list[MemberWork], int]:
    query: dict = {}
    if status:
        if status not in {item.value for item in WorkPublicationStatus}:
            raise AppError(422, "INVALID_STATUS", "Unknown publication status filter")
        query["publication_status"] = status
    if featured is not None:
        query["featured_on_projects"] = featured
    return await repository.list_works(
        query=query, sort=sort, skip=(page - 1) * page_size, limit=page_size
    )


async def decide_publication_review(
    admin: Admin, work_id: str, *, action: str, feedback: str | None
) -> MemberWork:
    """Record an admin publication-review decision.

    Only a work currently `pending_review` can be decided. `request_changes` and
    `reject` require feedback; `approve` publishes the work.
    """
    work = await get_for_admin(work_id)
    if work.publication_status != WorkPublicationStatus.PENDING_REVIEW:
        raise AppError(
            409, "WORK_NOT_IN_REVIEW", "This work is not awaiting review"
        )
    if action in ("request_changes", "reject") and not feedback:
        raise AppError(
            422,
            "FEEDBACK_REQUIRED",
            "Feedback is required when requesting changes or rejecting",
        )

    now = datetime.now(timezone.utc)
    fields: dict = {
        "reviewed_at": now,
        "reviewed_by": admin.id,
        "review_feedback": feedback,
    }
    if action == "approve":
        fields["publication_status"] = WorkPublicationStatus.PUBLISHED.value
        if work.published_at is None:
            fields["published_at"] = now
    elif action == "request_changes":
        fields["publication_status"] = WorkPublicationStatus.CHANGES_REQUESTED.value
    elif action == "reject":
        fields["publication_status"] = WorkPublicationStatus.REJECTED.value
    else:  # pragma: no cover - schema Literal guards this
        raise AppError(422, "INVALID_ACTION", "Unknown review action")

    updated = await repository.update_work(work_id, fields)
    if updated is None:  # pragma: no cover - deleted concurrently
        raise AppError(404, "WORK_NOT_FOUND", "Work was not found")
    return updated


async def set_featured(
    admin: Admin,
    work_id: str,
    *,
    featured: bool,
    classification: ProjectType | None,
) -> MemberWork:
    """Feature/unfeature a work on the official Projects page.

    Only a published, public-visible work can be featured; unfeaturing is always
    allowed. Membership profile eligibility is re-checked when the public
    listing is served, so a later profile change cannot leak a private work.
    """
    work = await get_for_admin(work_id)
    now = datetime.now(timezone.utc)
    if featured:
        if work.publication_status != WorkPublicationStatus.PUBLISHED:
            raise AppError(
                409,
                "WORK_NOT_PUBLISHED",
                "Only published works can be featured on the official Projects page",
            )
        if work.visibility != WorkVisibility.PUBLIC:
            raise AppError(
                409,
                "WORK_NOT_PUBLIC",
                "Only public-visible works can be featured on the official Projects page",
            )
        chosen = classification or ProjectType.MEMBER_CONTRIBUTION
        fields: dict = {
            "featured_on_projects": True,
            "featured_classification": chosen.value,
            "featured_at": work.featured_at or now,
            "featured_by": admin.id,
        }
    else:
        fields = {
            "featured_on_projects": False,
            "featured_classification": None,
            "featured_at": None,
            "featured_by": None,
        }
    updated = await repository.update_work(work_id, fields)
    if updated is None:  # pragma: no cover - deleted concurrently
        raise AppError(404, "WORK_NOT_FOUND", "Work was not found")
    return updated


# --------------------------------------------------------------------------
# Public surfaces (callers resolve the owner via members service first)
# --------------------------------------------------------------------------
async def list_featured_contributions(
    *, limit: int = 100
) -> list[tuple[MemberWork, Member]]:
    """Featured member works eligible for the public Projects page.

    Curated (featured) AND fully public-eligible: published + public work whose
    owner is active with a public profile. This mirrors the composite public
    rule, so featuring never widens visibility.
    """
    works, _ = await repository.list_works(
        query={
            "featured_on_projects": True,
            "publication_status": WorkPublicationStatus.PUBLISHED.value,
            "visibility": WorkVisibility.PUBLIC.value,
        },
        sort=[("featured_at", -1), ("published_at", -1)],
        skip=0,
        limit=limit,
    )
    results: list[tuple[MemberWork, Member]] = []
    owners: dict[str, Member | None] = {}
    for work in works:
        if work.member_id not in owners:
            owners[work.member_id] = await members_repository.find_by_id(work.member_id)
        member = owners[work.member_id]
        if member is None or member.status != MemberStatus.ACTIVE:
            continue
        if member.profile.profile_visibility != ProfileVisibility.PUBLIC:
            continue
        results.append((work, member))
    return results


def _is_public(work: MemberWork) -> bool:
    if work.publication_status != WorkPublicationStatus.PUBLISHED:
        return False
    return work.visibility == WorkVisibility.PUBLIC


async def get_public_work(owner: Member, slug: str) -> MemberWork:
    """Return a work only when it is published AND public-visible.

    The owner's active/public-profile status is already guaranteed by the
    caller (the public profile lookup that produced `owner`).
    """
    work = await repository.find_by_slug(owner.id, slug)
    if work is None or not _is_public(work):
        raise AppError(404, "WORK_NOT_FOUND", "Work was not found")
    return work


async def get_public_work_by_id(owner: Member, work_id: str) -> MemberWork:
    """Return the owner's work by its stable internal id when it is published
    AND public-visible. Unlike slug lookup this survives renames, so a link to a
    work's current version keeps resolving after the member edits its title.
    """
    work = await repository.find_by_id(work_id)
    if work is None or work.member_id != owner.id or not _is_public(work):
        raise AppError(404, "WORK_NOT_FOUND", "Work was not found")
    return work


async def list_public_works_for_owner(
    owner: Member, *, page_size: int = 50
) -> list[MemberWork]:
    works, _ = await repository.list_works(
        query={
            "member_id": owner.id,
            "publication_status": WorkPublicationStatus.PUBLISHED.value,
            "visibility": WorkVisibility.PUBLIC.value,
        },
        sort=[("published_at", -1), ("created_at", -1)],
        skip=0,
        limit=page_size,
    )
    return works


async def list_public_works_for_sitemap(*, page_size: int = 1000) -> list[tuple[str, str]]:
    """Return (readable member_id, slug) pairs for every public work."""
    works, _ = await repository.list_works(
        query={
            "publication_status": WorkPublicationStatus.PUBLISHED.value,
            "visibility": WorkVisibility.PUBLIC.value,
        },
        sort=[("published_at", -1)],
        skip=0,
        limit=page_size,
    )
    results: list[tuple[str, str]] = []
    owners: dict[str, Member | None] = {}
    for work in works:
        if work.member_id not in owners:
            owners[work.member_id] = await members_repository.find_by_id(work.member_id)
        member = owners[work.member_id]
        if member is None or member.status != MemberStatus.ACTIVE:
            continue
        if member.profile.profile_visibility != ProfileVisibility.PUBLIC:
            continue
        results.append((member.member_id, work.slug))
    return results