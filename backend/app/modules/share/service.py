"""Resolve public entities into share cards + preview images.

Everything flows through the *existing* public services (`get_public_member`,
`get_public_project_by_slug`, `get_public_work`), so the share surfaces inherit
the exact same visibility rules — private profiles, unpublished works, drafts
and archived projects all 404 identically and can never leak.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Iterable

from fastapi import Request

from app.core.config import get_settings
from app.core.errors import AppError
from app.core.logging import get_logger
from app.modules.branding import service as branding_service
from app.modules.media import service as media_service
from app.modules.members import service as members_service
from app.modules.projects import service as projects_service
from app.modules.works import service as works_service

from .metadata import ShareCard, clean_title
from .preview import render_preview_image

log = get_logger("share")

_DEFAULT_ACCENT = "#f59e0b"
_WHITESPACE = re.compile(r"\s+")


@dataclass(frozen=True)
class SharePayload:
    card: ShareCard
    background: bytes | None = None
    # A media id used only when `background` is None (branding OG image for the
    # site card). Never an alternate entity's asset.
    branded_media_id: str | None = None


def _public_base(request: Request) -> str:
    settings = get_settings()
    base = (settings.FRONTEND_URL or "").strip().rstrip("/")
    if base:
        return base
    # Local/dev fallback only — production always sets FRONTEND_URL.
    return str(request.base_url).rstrip("/")


def _footer(base: str) -> str:
    host = base.split("://", 1)[-1].rstrip("/")
    return host or "thridhalabs.com"


def _short(value: str | None, limit: int = 120) -> str | None:
    if not value:
        return None
    cleaned = _WHITESPACE.sub(" ", value).strip()
    if not cleaned:
        return None
    if len(cleaned) <= limit:
        return cleaned
    return cleaned[: limit - 1].rstrip(" ,;:.-") + "…"


async def _accent() -> str:
    try:
        branding = await branding_service.get_branding()
        colour = branding.colors.accent
        if colour:
            return colour
    except Exception:  # branding is best-effort presentation data
        log.warning("Falling back to the default accent (branding unavailable)")
    return _DEFAULT_ACCENT


async def _background_from_id(media_id: str | None) -> bytes | None:
    """Read a usable image for one media id, or None."""
    if not media_id:
        return None
    for variant in ("lg", "md", "original"):
        try:
            data, _mime = await media_service.get_media_file(media_id, variant)
            return data
        except AppError:
            continue
        except Exception:  # storage hiccup must not break the share document
            log.warning("Background media read failed (variant=%s)", variant)
            break
    return None


async def _background(media_ids: Iterable[str | None]) -> bytes | None:
    """First usable image across an ordered candidate list, or None.

    Candidates are tried in order (explicit cover first, then content/gallery
    fallbacks) so a card always prefers the entity's own intended image and
    never borrows another entity's asset.
    """
    for media_id in media_ids:
        data = await _background_from_id(media_id)
        if data is not None:
            return data
    return None


def _work_image_candidates(work: object) -> list[str | None]:
    """Work cover first, then the first public image from its content blocks."""
    candidates: list[str | None] = [getattr(work, "cover_media_id", None)]
    content = getattr(work, "content", None)
    if content is not None:
        candidates.extend(content.media_ids())
    return candidates


def _project_image_candidates(project: object) -> list[str | None]:
    """Project cover (thumbnail) first, then the first gallery image."""
    candidates: list[str | None] = [getattr(project, "thumbnail_media_id", None)]
    gallery = getattr(project, "gallery_media_ids", None) or []
    candidates.extend(gallery)
    return candidates


async def member_payload(request: Request, member_id: str) -> SharePayload:
    member = await members_service.get_public_member(member_id)
    name = member.profile.display_name or member.full_name or member.member_id
    base = _public_base(request)
    canonical = f"{base}/members/{member.member_id}"
    image = f"{base}/share/members/{member.member_id}/image"
    description = _short(member.profile.bio) or f"{name} — member of Thridha Labs."
    card = ShareCard(
        kind="member",
        title=clean_title(f"{name} — Thridha Labs"),
        description=description,
        canonical_url=canonical,
        image_url=image,
        image_alt=f"Portrait of {name}",
        og_type="profile",
        kicker=f"Member · {member.member_id}",
        subtitle=_short(member.profile.bio, 110),
        footer=_footer(base),
    )
    background = await _background([member.profile.picture_media_id])
    return SharePayload(card=card, background=background)


async def project_payload(request: Request, slug: str) -> SharePayload:
    project, _client = await projects_service.get_public_project_by_slug(slug)
    base = _public_base(request)
    canonical = f"{base}/projects/{project.slug}"
    image = f"{base}/share/projects/{project.slug}/image"
    description = _short(project.description) or f"{project.name} — a project by Thridha Labs."
    card = ShareCard(
        kind="project",
        title=clean_title(f"{project.name} — Thridha Labs"),
        description=description,
        canonical_url=canonical,
        image_url=image,
        image_alt=f"Preview of the {project.name} project",
        og_type="website",
        kicker="Project",
        subtitle=_short(project.description, 110),
        footer=_footer(base),
    )
    background = await _background(_project_image_candidates(project))
    return SharePayload(card=card, background=background)


async def work_payload(request: Request, member_id: str, slug: str) -> SharePayload:
    owner = await members_service.get_public_member(member_id)
    work = await works_service.get_public_work(owner, slug)
    author = owner.profile.display_name or owner.full_name or owner.member_id
    base = _public_base(request)
    canonical = f"{base}/members/{owner.member_id}/works/{work.slug}"
    image = f"{base}/share/members/{owner.member_id}/works/{work.slug}/image"
    description = _short(work.summary) or f"A work by {author}."
    card = ShareCard(
        kind="work",
        title=clean_title(f"{work.title} — Thridha Labs"),
        description=description,
        canonical_url=canonical,
        image_url=image,
        image_alt=f"Cover image for {work.title} by {author}",
        og_type="article",
        kicker=f"Work · {author}",
        subtitle=_short(work.summary, 110),
        footer=_footer(base),
    )
    background = await _background(_work_image_candidates(work))
    return SharePayload(card=card, background=background)


async def _branding_media_id() -> str | None:
    try:
        branding = await branding_service.get_branding()
        # Priority: admin og_image, else admin logo variants for social sharing
        return branding.media.og_image or branding.media.logo or branding.media.logo_light or branding.media.logo_dark
    except Exception:  # branding is best-effort presentation data
        log.warning("Branding media unavailable for the site card")
        return None


async def site_payload(request: Request) -> SharePayload:
    """The branded general-purpose card for the homepage and non-entity pages.

    Hero image priority: admin og_image/logo, else default thridhalabs logo asset.
    """
    base = _public_base(request)
    card = ShareCard(
        kind="site",
        title=clean_title("Thridha Labs - AI & software experimentation lab"),
        description=(
            "Thridha Labs is a technology and AI experimentation lab. AI, "
            "software and ideas turned into things people can actually use."
        ),
        canonical_url=f"{base}/",
        image_url=f"{base}/share/site/image",
        image_alt="Thridha Labs - AI and software experimentation lab",
        og_type="website",
        kicker="Thridha Labs",
        subtitle=None,
        footer=_footer(base),
    )
    return SharePayload(card=card, branded_media_id=await _branding_media_id())


async def render(payload: SharePayload) -> bytes:
    """Render the 1200x630 JPEG for a resolved payload."""
    accent = await _accent()
    background = payload.background
    if background is None and payload.branded_media_id:
        background = await _background_from_id(payload.branded_media_id)
    # Fallback to default logo if nothing else available
    if background is None and payload.card.kind == "site":
        try:
            from app.modules.branding_defaults import service as branding_defaults_service

            bg = branding_defaults_service.get_default_logo_bytes()
            if bg:
                background = bg
        except Exception:
            pass
    return render_preview_image(
        title=clean_title(payload.card.title).replace(" - Thridha Labs", "").replace(" — Thridha Labs", ""),
        kicker=payload.card.kicker,
        subtitle=payload.card.subtitle,
        footer=payload.card.footer,
        background=background,
        accent=accent,
    )
