"""Health endpoints: liveness (/health) and readiness (/health/ready)."""

from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Response

from app.core.config import get_settings
from app.db.mongo import get_mongo

router = APIRouter(tags=["health"])


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


@router.get("/health")
async def health() -> dict:
    settings = get_settings()
    return {
        "status": "ok",
        "app": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "environment": "development" if settings.DEBUG else "production",
        "timestamp": _now(),
    }


@router.get("/health/ready")
async def health_ready(response: Response) -> dict:
    settings = get_settings()
    ok, latency_ms = await get_mongo().ping_with_latency(settings)
    if not ok:
        response.status_code = 503
    return {
        "status": "ready" if ok else "degraded",
        "checks": {
            "mongo": "up" if ok else "down",
            "latency_ms": latency_ms,
        },
        "timestamp": _now(),
    }
