"""FastAPI application entry point for the Thridha Labs platform."""

from __future__ import annotations

from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes.health import router as health_router
from app.api.routes.seo import router as seo_router
from app.modules.share.router import router as share_router
from app.core.config import ConfigurationError, get_settings
from app.core.errors import register_exception_handlers
from app.core.logging import configure_logging, get_logger
from app.db.indexes import ensure_indexes
from app.db.mongo import get_mongo
from app.modules.auth.router import router as auth_router
from app.modules.activities.member import router as activities_member_router
from app.modules.activities.public import router as activities_public_router
from app.modules.activities.router import router as activities_router
from app.modules.ai.router import router as ai_summaries_router
from app.modules.ai.settings_router import router as ai_settings_router
from app.modules.reports.admin_router import router as reports_admin_router
from app.modules.reports.router import router as reports_router
from app.modules.activity_submissions.admin_router import (
    router as activity_submissions_admin_router,
)
from app.modules.activity_submissions.member_router import (
    router as activity_workspaces_member_router,
)
from app.modules.activity_submissions.member_router import (
    submissions_router as activity_submissions_member_router,
)
from app.modules.branding.public import router as branding_public_router
from app.modules.branding.router import router as branding_router
from app.modules.branding_defaults.router import router as branding_defaults_router
from app.modules.careers.public import router as careers_public_router
from app.modules.careers.router import router as careers_router
from app.modules.certifications.admin_router import router as certifications_admin_router
from app.modules.certifications.router import router as certifications_router
from app.modules.certificates.admin_router import router as certificates_admin_router
from app.modules.certificates.public import router as certificates_public_router
from app.modules.certificates.router import router as certificates_router
from app.modules.activity_certificates.admin_router import (
    router as activity_certificates_admin_router,
)
from app.modules.activity_certificates.public import (
    router as activity_certificates_public_router,
)
from app.modules.activity_certificates.router import (
    router as activity_certificates_router,
)
from app.modules.clients.public import router as clients_public_router
from app.modules.clients.router import router as clients_router
from app.modules.media.public import router as media_public_router
from app.modules.media.router import router as media_router
from app.modules.members.admin_router import router as members_admin_router
from app.modules.members.public import router as members_public_router
from app.modules.members.router import router as member_router
from app.modules.projects.public import router as projects_public_router
from app.modules.projects.router import router as projects_router
from app.modules.settings.public import router as settings_public_router
from app.modules.settings.router import router as settings_router
from app.modules.testimonials.public import router as testimonials_public_router
from app.modules.testimonials.router import router as testimonials_router
from app.modules.works.admin_router import router as works_admin_router
from app.modules.works.public import contributions_router as works_contributions_router
from app.modules.works.public import router as works_public_router
from app.modules.works.router import router as works_router
from app.modules.legal.public import router as legal_public_router
from app.modules.legal.router import router as legal_router
from app.storage import get_storage_provider


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    settings = get_settings()
    configure_logging(settings)
    log = get_logger("app")

    log.info(
        "Starting %s %s | debug=%s | log_level=%s | prefix=%s | storage=%s | db=%s | cors_origins=%d",
        settings.APP_NAME,
        settings.APP_VERSION,
        settings.DEBUG,
        settings.LOG_LEVEL,
        settings.API_PREFIX,
        settings.STORAGE_MODE,
        settings.MONGO_DB_NAME,
        len(settings.cors_origin_list),
    )

    ready = await get_mongo().connect(settings)
    if ready:
        log.info("MongoDB reachable â€” database '%s'", settings.MONGO_DB_NAME)
        # Indexes (e.g. admins.email unique) are created at startup; a failure
        # here breaks account uniqueness guarantees, so it fails fast.
        await ensure_indexes()
    else:
        log.warning(
            "MongoDB not reachable at startup â€” /api/health/ready will report degraded"
        )

    # Fail fast on a misconfigured storage provider (e.g. S3 without AWS_*).
    try:
        storage = get_storage_provider()
    except ConfigurationError as exc:
        log.error("Invalid storage configuration â€” refusing to start: %s", exc)
        raise
    log.info("Storage provider initialised (mode=%s)", storage.mode)

    try:
        yield
    finally:
        await get_mongo().close()
        log.info("Shutdown complete")


def create_app() -> FastAPI:
    settings = get_settings()

    app = FastAPI(
        title=f"{settings.APP_NAME} API",
        version=settings.APP_VERSION,
        lifespan=lifespan,
        docs_url=f"{settings.API_PREFIX}/docs",
        redoc_url=None,
        openapi_url=f"{settings.API_PREFIX}/openapi.json",
    )

    # Cookie-based auth (Phase 2) requires credentials; the origin list comes
    # from CORS_ORIGINS and is validated never to contain '*'.
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
        allow_headers=["*"],
    )

    app.include_router(health_router, prefix=settings.API_PREFIX)
    app.include_router(auth_router, prefix=settings.API_PREFIX)
    app.include_router(media_router, prefix=settings.API_PREFIX)
    # Content APIs (Phase 4)
    app.include_router(settings_router, prefix=settings.API_PREFIX)
    app.include_router(branding_router, prefix=settings.API_PREFIX)
    app.include_router(clients_router, prefix=settings.API_PREFIX)
    app.include_router(projects_router, prefix=settings.API_PREFIX)
    app.include_router(testimonials_router, prefix=settings.API_PREFIX)
    app.include_router(careers_router, prefix=settings.API_PREFIX)
    # Member accounts (Phase 9): admin management + member self-service.
    app.include_router(members_admin_router, prefix=settings.API_PREFIX)
    app.include_router(member_router, prefix=settings.API_PREFIX)
    # Activities (Phase 1): admin management, member self-registration + public.
    app.include_router(activities_router, prefix=settings.API_PREFIX)
    app.include_router(activities_member_router, prefix=settings.API_PREFIX)
    # Project progress reports: member submission + admin review.
    app.include_router(reports_router, prefix=settings.API_PREFIX)
    app.include_router(reports_admin_router, prefix=settings.API_PREFIX)
    app.include_router(activity_submissions_member_router, prefix=settings.API_PREFIX)
    app.include_router(activity_workspaces_member_router, prefix=settings.API_PREFIX)
    app.include_router(activity_submissions_admin_router, prefix=settings.API_PREFIX)
    # Groq AI work summaries: admin-only settings + draft/publish workflow.
    app.include_router(ai_settings_router, prefix=settings.API_PREFIX)
    app.include_router(ai_summaries_router, prefix=settings.API_PREFIX)
    # Work showcase + publication review + certification review.
    app.include_router(works_router, prefix=settings.API_PREFIX)
    app.include_router(works_admin_router, prefix=settings.API_PREFIX)
    app.include_router(certifications_router, prefix=settings.API_PREFIX)
    app.include_router(certifications_admin_router, prefix=settings.API_PREFIX)
    # Certificates: issuance, verification, download, delivery.
    app.include_router(certificates_router, prefix=settings.API_PREFIX)
    app.include_router(certificates_admin_router, prefix=settings.API_PREFIX)
    # Activity certificates: separate subsystem for programmes/hackathons.
    app.include_router(activity_certificates_router, prefix=settings.API_PREFIX)
    app.include_router(activity_certificates_admin_router, prefix=settings.API_PREFIX)
    # Public content APIs
    app.include_router(settings_public_router, prefix=settings.API_PREFIX)
    app.include_router(branding_public_router, prefix=settings.API_PREFIX)
    app.include_router(clients_public_router, prefix=settings.API_PREFIX)
    app.include_router(projects_public_router, prefix=settings.API_PREFIX)
    app.include_router(testimonials_public_router, prefix=settings.API_PREFIX)
    app.include_router(careers_public_router, prefix=settings.API_PREFIX)
    app.include_router(media_public_router, prefix=settings.API_PREFIX)
    app.include_router(members_public_router, prefix=settings.API_PREFIX)
    app.include_router(works_public_router, prefix=settings.API_PREFIX)
    app.include_router(works_contributions_router, prefix=settings.API_PREFIX)
    app.include_router(certificates_public_router, prefix=settings.API_PREFIX)
    app.include_router(activity_certificates_public_router, prefix=settings.API_PREFIX)
    app.include_router(activities_public_router, prefix=settings.API_PREFIX)
    app.include_router(legal_public_router, prefix=settings.API_PREFIX)
    app.include_router(legal_router, prefix=settings.API_PREFIX)

    # Top-level SEO documents (no /api prefix).
    app.include_router(seo_router)
    # Default branding assets (no /api prefix) - public, cached.
    app.include_router(branding_defaults_router)
    # Top-level social share documents + generated preview images (no /api
    # prefix) �?" routed to crawlers by the reverse proxy.
    app.include_router(share_router)
    register_exception_handlers(app)
    return app


try:
    app = create_app()
except ConfigurationError as exc:  # pragma: no cover - fail-fast at import/boot
    raise SystemExit(f"FATAL: {exc}") from exc


if __name__ == "__main__":  # pragma: no cover
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host="127.0.0.1",
        port=8000,
        reload=get_settings().DEBUG,
    )

