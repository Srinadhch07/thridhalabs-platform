"""Site-level SEO documents: /sitemap.xml and /robots.txt.

Served at the repository root (outside the /api prefix) so crawlers can
discover them with conventional requests. All sitemap URLs derive from
`settings.FRONTEND_URL` — never localhost — and only published public routes
are included.
"""

from __future__ import annotations

from fastapi import APIRouter, Response

from app.core.config import get_settings
from app.modules.activities import service as activities_service
from app.modules.careers import service as careers_service
from app.modules.projects import service as projects_service
from app.modules.works import service as works_service

router = APIRouter()

_SITEMAP_NS = "http://www.sitemaps.org/schemas/sitemap/0.9"

# Static public routes (align with the frontend AppRouter).
_STATIC_PATHS = ("/", "/projects", "/activities", "/clients", "/testimonials", "/about", "/contact")


def _absolute(base: str, path: str) -> str:
    return f"{base.rstrip('/')}{path}"


@router.get("/sitemap.xml", include_in_schema=False)
async def sitemap() -> Response:
    settings = get_settings()
    base = settings.FRONTEND_URL or ""
    if not base:
        # Refuse to emit an empty/invalid sitemap — a missing public URL is a
        # deployment misconfiguration rather than a cacheable document.
        return Response(status_code=503)

    urls: list[str] = [_absolute(base, path) for path in _STATIC_PATHS]

    try:
        careers = await careers_service.get_settings()
        if careers.enabled:
            urls.append(_absolute(base, "/careers"))
    except Exception:
        # A careers configuration problem must not break the sitemap.
        from app.core.logging import get_logger

        get_logger("seo").exception("Sitemap generation failed for the careers entry")

    try:
        projects, _refs, total = await projects_service.list_public_projects(
            page=1,
            page_size=1000,
            category=None,
            project_type=None,
            featured=None,
            sort=[("display_order", 1)],
        )
        urls.extend(_absolute(base, f"/projects/{project.slug}") for project in projects)
        if total > len(projects):
            # This phase paginates at a high ceiling; log rather than loop.
            from app.core.logging import get_logger

            get_logger("seo").warning("Sitemap pagination truncated at %d projects", len(projects))
    except Exception:
        # The sitemap must never 500 — fall back to the static routes only.
        from app.core.logging import get_logger

        get_logger("seo").exception("Sitemap generation failed for project entries")

    try:
        # Public member profiles + their published public works. Both derive
        # from the same visibility rules the public APIs enforce.
        entries = await works_service.list_public_works_for_sitemap()
        seen_members: set[str] = set()
        for member_id, slug in entries:
            if member_id not in seen_members:
                seen_members.add(member_id)
                urls.append(_absolute(base, f"/members/{member_id}"))
            urls.append(_absolute(base, f"/members/{member_id}/works/{slug}"))
    except Exception:
        from app.core.logging import get_logger

        get_logger("seo").exception("Sitemap generation failed for member work entries")

    try:
        # Published activities only (cancelled/archived/draft are never listed).
        activities, _total = await activities_service.list_public(
            page=1,
            page_size=1000,
            activity_type=None,
            featured=None,
            sort=[("display_order", 1)],
        )
        urls.extend(
            _absolute(base, f"/activities/{activity.slug}") for activity in activities
        )
    except Exception:
        from app.core.logging import get_logger

        get_logger("seo").exception("Sitemap generation failed for activity entries")

    body = "\n".join(
        [
            '<?xml version="1.0" encoding="UTF-8"?>',
            f'<urlset xmlns="{_SITEMAP_NS}">',
            *[f"  <url><loc>{url}</loc></url>" for url in urls],
            "</urlset>",
            "",
        ]
    )
    return Response(content=body, media_type="application/xml")


@router.get("/robots.txt", include_in_schema=False)
async def robots() -> Response:
    settings = get_settings()
    base = settings.FRONTEND_URL or ""
    if not base:
        return Response(status_code=503)

    body = "\n".join(
        [
            "User-agent: *",
            "Allow: /",
            "Disallow: /admin",
            "Disallow: /admin/*",
            "Disallow: /member",
            "Disallow: /member/*",
            "Disallow: /verify-certificate",
            "Disallow: /verify-certificate/*",
            "Disallow: /verify-activity-certificate",
            "Disallow: /verify-activity-certificate/*",
            f"Sitemap: {_absolute(base, '/sitemap.xml')}",
            "",
        ]
    )
    return Response(content=body, media_type="text/plain")
