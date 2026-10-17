"""Resolve public entities into share cards + preview images.

Everything flows through the *existing* public services (`get_public_member`,
`get_public_project_by_slug`, `get_public_work`), so the share surfaces inherit
the exact same visibility rules — private profiles, unpublished works, drafts
and archived projects all 404 identically and can never leak.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

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
    background: bytes | None


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


async def _background(media_id: str | None) -> bytes | None:
    """Read a usable image for the card background, or None for the fallback."""
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
    return SharePayload(card=card, background=await _background(member.profile.picture_media_id))


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
    return SharePayload(card=card, background=await _background(project.thumbnail_media_id))


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
    return SharePayload(card=card, background=await _background(work.cover_media_id))


async def render(payload: SharePayload) -> bytes:
    """Render the 1200x630 JPEG for a resolved payload."""
    accent = await _accent()
    return render_preview_image(
        title=clean_title(payload.card.title).replace(" — Thridha Labs", ""),
        kicker=payload.card.kicker,
        subtitle=payload.card.subtitle,
        footer=payload.card.footer,
        background=payload.background,
        accent=accent,
    )
