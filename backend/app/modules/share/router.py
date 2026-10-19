"""Share routes — crawler-readable HTML + generated preview images.

Mounted at the repository root (no `/api` prefix), alongside `/sitemap.xml` and
`/robots.txt`, so the reverse proxy can map the canonical public page paths to
these documents for social crawlers without touching the SPA.

- `GET /share/members/{member_id}`                → member profile card
- `GET /share/members/{member_id}/image`          → 1200x630 JPEG
- `GET /share/projects/{slug}`                    → project card
- `GET /share/projects/{slug}/image`              → 1200x630 JPEG
- `GET /share/members/{member_id}/works/{slug}`   → work card
- `GET /share/members/{member_id}/works/{slug}/image` → 1200x630 JPEG
- `GET /share/site`                                → branded general card
- `GET /share/site/image`                          → 1200x630 JPEG

Unknown, private or unpublished targets return an identical `noindex` 404 —
existence is never leaked. Maintenance mode short-circuits with the standard
`503 MAINTENANCE_MODE` JSON response, exactly like the public content APIs.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Request, Response
from fastapi.responses import HTMLResponse

from app.core.errors import AppError
from app.deps.maintenance import require_public_site_available

from . import service
from .metadata import render_not_found_html, render_share_html

router = APIRouter(
    tags=["share"],
    include_in_schema=False,
    dependencies=[Depends(require_public_site_available)],
)

_HTML_CACHE = "public, max-age=300"
_IMAGE_CACHE = "public, max-age=3600"


def _html_response(body: str, *, status_code: int = 200) -> Response:
    return HTMLResponse(
        content=body,
        status_code=status_code,
        headers={"Cache-Control": _HTML_CACHE if status_code == 200 else "no-store"},
    )


def _not_found() -> Response:
    return _html_response(render_not_found_html(), status_code=404)


def _image_response(data: bytes) -> Response:
    return Response(
        content=data,
        media_type="image/jpeg",
        headers={"Cache-Control": _IMAGE_CACHE},
    )


async def _card_or_404(build, *args) -> Response:
    try:
        payload = await build(*args)
    except AppError as exc:
        if exc.status_code == 404:
            return _not_found()
        raise
    return _html_response(render_share_html(payload.card))


async def _image_or_404(build, *args) -> Response:
    # A missing entity raises the standard 404 error envelope (the HTML
    # document that referenced this image is itself a 404).
    payload = await build(*args)
    return _image_response(await service.render(payload))


@router.get("/share/site")
async def share_site(request: Request) -> Response:
    """The branded general-purpose document for the homepage and pages with no
    dedicated share surface (About, Projects list, Clients, Testimonials, …)."""
    payload = await service.site_payload(request)
    return _html_response(render_share_html(payload.card))


@router.get("/share/site/image")
async def share_site_image(request: Request) -> Response:
    payload = await service.site_payload(request)
    return _image_response(await service.render(payload))


@router.get("/share/members/{member_id}")
async def share_member(member_id: str, request: Request) -> Response:
    return await _card_or_404(service.member_payload, request, member_id)


@router.get("/share/members/{member_id}/image")
async def share_member_image(member_id: str, request: Request) -> Response:
    return await _image_or_404(service.member_payload, request, member_id)


@router.get("/share/projects/{slug}")
async def share_project(slug: str, request: Request) -> Response:
    return await _card_or_404(service.project_payload, request, slug)


@router.get("/share/projects/{slug}/image")
async def share_project_image(slug: str, request: Request) -> Response:
    return await _image_or_404(service.project_payload, request, slug)


@router.get("/share/members/{member_id}/works/{slug}")
async def share_work(member_id: str, slug: str, request: Request) -> Response:
    return await _card_or_404(service.work_payload, request, member_id, slug)


@router.get("/share/members/{member_id}/works/{slug}/image")
async def share_work_image(member_id: str, slug: str, request: Request) -> Response:
    return await _image_or_404(service.work_payload, request, member_id, slug)
