"""Structured logging setup.

Respects LOG_LEVEL and DEBUG. Logs must never contain passwords, JWT secrets,
cookies, authorization headers, cloud credentials, database credentials,
SMTP passwords or raw `.env` values — wrap secrets in `SecretStr` and log
only non-sensitive identifiers.
"""

from __future__ import annotations

import logging
import sys

from app.core.config import Settings

_FORMAT = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"
_DATEFMT = "%Y-%m-%d %H:%M:%S"


def effective_level(settings: Settings) -> int:
    """Resolve the runtime level from LOG_LEVEL, tightened by DEBUG."""
    level = logging.getLevelName(settings.LOG_LEVEL)
    if not isinstance(level, int):  # pragma: no cover - Literal guarantees this
        level = logging.WARNING
    if settings.DEBUG and level > logging.DEBUG:
        level = logging.DEBUG
    return level


def configure_logging(settings: Settings) -> None:
    level = effective_level(settings)
    logging.basicConfig(
        level=level,
        format=_FORMAT,
        datefmt=_DATEFMT,
        stream=sys.stdout,
        force=True,
    )
    # Keep third-party access chatter aligned with our level.
    logging.getLogger("uvicorn.access").setLevel(max(level, logging.INFO))
    logging.getLogger("motor").setLevel(max(level, logging.WARNING))


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)
