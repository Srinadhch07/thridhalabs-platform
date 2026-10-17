"""MongoDB connection layer.

Provides client creation, database access, connection lifecycle (connect /
health check / clean shutdown). No business collections or models are defined
in this phase.
"""

from __future__ import annotations

import time

from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from pymongo.errors import PyMongoError

from app.core.config import Settings, get_settings
from app.core.logging import get_logger

log = get_logger("db.mongo")


class Mongo:
    """Async MongoDB lifecycle wrapper (process-wide singleton)."""

    def __init__(self) -> None:
        self._client: AsyncIOMotorClient | None = None

    # -- lifecycle ---------------------------------------------------
    async def connect(self, settings: Settings | None = None) -> bool:
        """Create the client and verify reachability. Returns readiness."""
        settings = settings or get_settings()
        if self._client is None:
            self._client = AsyncIOMotorClient(
                settings.MONGO_URI.get_secret_value(),
                serverSelectionTimeoutMS=settings.MONGO_TIMEOUT_MS,
                connectTimeoutMS=settings.MONGO_TIMEOUT_MS,
            )
        return await self.ping(settings)

    async def ping(self, settings: Settings | None = None) -> bool:
        """Round-trip check against the server (safe to call repeatedly)."""
        if self._client is None:
            await self.connect(settings)
        if self._client is None:  # pragma: no cover - defensive
            return False
        settings = settings or get_settings()
        started = time.monotonic()
        try:
            await self._client.admin.command("ping")
            return True
        except PyMongoError as exc:
            # Only the exception type is logged: connection strings may carry
            # credentials and must never reach the logs.
            log.warning(
                "MongoDB ping failed (%s) after %.0f ms",
                type(exc).__name__,
                (time.monotonic() - started) * 1000,
            )
            return False

    async def ping_with_latency(self, settings: Settings | None = None) -> tuple[bool, int | None]:
        """Ping and report (reachable, latency_ms)."""
        started = time.monotonic()
        ok = await self.ping(settings)
        latency = int((time.monotonic() - started) * 1000)
        return ok, (latency if ok else None)

    async def close(self) -> None:
        if self._client is not None:
            self._client.close()
            self._client = None
            log.info("MongoDB client closed")

    # -- accessors ---------------------------------------------------
    @property
    def is_connected(self) -> bool:
        return self._client is not None

    @property
    def database(self) -> AsyncIOMotorDatabase:
        if self._client is None:
            raise RuntimeError("MongoDB client is not initialised — call connect() first")
        return self._client[get_settings().MONGO_DB_NAME]


mongo = Mongo()


def get_mongo() -> Mongo:
    return mongo
