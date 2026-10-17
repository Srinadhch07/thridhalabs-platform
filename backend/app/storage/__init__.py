"""Storage provider selection — the one place that maps configuration to a
concrete `StorageProvider`. Application code never touches boto3 or the
filesystem directly; it only ever calls `get_storage_provider()`."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from app.core.config import REPO_ROOT, ConfigurationError, get_settings
from app.storage.base import (  # noqa: F401  (re-exported for convenience)
    InvalidKeyError,
    StorageError,
    StorageObjectNotFoundError,
    StorageProvider,
    validate_object_key,
)
from app.storage.local import LocalStorageProvider
from app.storage.s3 import S3StorageProvider

STORAGE_MODES = ("local", "s3")


@lru_cache(maxsize=1)
def get_storage_provider() -> StorageProvider:
    """Build (and cache) the provider configured by ``STORAGE_MODE``.

    Cache is process-wide; call ``get_storage_provider.cache_clear()`` after
    changing settings (tests do this).
    """
    settings = get_settings()

    if settings.STORAGE_MODE == "local":
        raw = settings.STORAGE_LOCAL_DIR.strip() or "storage-local"
        root = Path(raw)
        if not root.is_absolute():
            root = REPO_ROOT / root
        return LocalStorageProvider(root.resolve())

    if settings.STORAGE_MODE == "s3":
        access_key = (
            settings.AWS_ACCESS_KEY_ID.get_secret_value()
            if settings.AWS_ACCESS_KEY_ID
            else ""
        )
        secret_key = (
            settings.AWS_SECRET_ACCESS_KEY.get_secret_value()
            if settings.AWS_SECRET_ACCESS_KEY
            else ""
        )
        missing = [
            name
            for name, value in (
                ("AWS_REGION", settings.AWS_REGION),
                ("AWS_S3_BUCKET", settings.AWS_S3_BUCKET),
                ("AWS_ACCESS_KEY_ID", access_key),
                ("AWS_SECRET_ACCESS_KEY", secret_key),
            )
            if not value
        ]
        if missing:
            raise ConfigurationError(
                "STORAGE_MODE='s3' requires "
                + ", ".join(missing)
                + " to be configured"
            )
        return S3StorageProvider(
            region=settings.AWS_REGION,
            bucket=settings.AWS_S3_BUCKET,
            access_key=access_key,
            secret_key=secret_key,
        )

    # Literal validation in Settings already prevents this; defensive only.
    raise ConfigurationError(  # pragma: no cover - unreachable
        f"Unsupported STORAGE_MODE: {settings.STORAGE_MODE!r}"
        f" (expected one of {STORAGE_MODES})"
    )