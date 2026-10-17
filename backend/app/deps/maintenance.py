"""Public-site availability guard for maintenance mode.

When the admin enables `maintenance_mode`, public content endpoints answer
503 (with a stable `MAINTENANCE_MODE` code the frontend already renders as its
maintenance page) instead of serving content. Deliberately NOT applied to:
admin APIs, authentication, health checks, sitemap/robots, or the public
settings/branding endpoints the frontend needs to render the maintenance
notice itself. No redirects — so no redirect loops are possible.
"""

from __future__ import annotations

from app.core.errors import AppError
from app.modules.settings import service as settings_service


async def require_public_site_available() -> None:
    settings = await settings_service.get_settings()
    if settings.maintenance_mode:
        raise AppError(
            503,
            "MAINTENANCE_MODE",
            "The site is temporarily offline for maintenance",
        )
