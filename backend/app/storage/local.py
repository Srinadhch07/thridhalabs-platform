"""Local filesystem storage provider."""

from __future__ import annotations

import asyncio
import os
from pathlib import Path

from app.storage.base import (
    StorageError,
    StorageObjectNotFoundError,
    StorageProvider,
    validate_object_key,
)


class LocalStorageProvider(StorageProvider):
    """Stores objects as files under a configured root directory.

    Safety properties:

    - Keys are validated (relative, safe characters, no ``..`` / absolute
      paths / separators) before any filesystem access. User-controlled names
      never become filesystem paths.
    - Writes are atomic: data goes to a temp file in the same directory and is
      moved into place with ``os.replace``.
    - Deletion is idempotent (missing objects are a no-op).
    """

    def __init__(self, root: Path) -> None:
        self._root = root.resolve()

    @property
    def mode(self) -> str:
        return "local"

    @property
    def root(self) -> Path:
        """The resolved storage root (used by tests/administration)."""
        return self._root

    def _resolve(self, key: str) -> Path:
        validate_object_key(key)
        return self._root.joinpath(*key.split("/"))

    # -- async wrappers -----------------------------------------------------
    async def put(
        self,
        key: str,
        data: bytes,
        content_type: str = "application/octet-stream",
    ) -> None:
        await asyncio.to_thread(self._put_sync, key, data)

    async def get(self, key: str) -> bytes:
        return await asyncio.to_thread(self._get_sync, key)

    async def delete(self, key: str) -> None:
        await asyncio.to_thread(self._delete_sync, key)

    async def exists(self, key: str) -> bool:
        return await asyncio.to_thread(self._exists_sync, key)

    # -- synchronous implementations ---------------------------------------
    def _put_sync(self, key: str, data: bytes) -> None:
        dest = self._resolve(key)
        dest.parent.mkdir(parents=True, exist_ok=True)
        tmp = dest.with_name(f".{dest.name}.{os.getpid()}.tmp")
        try:
            with open(tmp, "wb") as handle:
                handle.write(data)
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(tmp, dest)
        except OSError as exc:
            raise StorageError(f"Failed to store object '{key}'") from exc
        finally:
            if tmp.exists():
                try:
                    tmp.unlink()
                except OSError:
                    pass

    def _get_sync(self, key: str) -> bytes:
        path = self._resolve(key)
        try:
            with open(path, "rb") as handle:
                return handle.read()
        except FileNotFoundError as exc:
            raise StorageObjectNotFoundError(f"Object not found: '{key}'") from exc
        except OSError as exc:
            raise StorageError(f"Failed to read object '{key}'") from exc

    def _delete_sync(self, key: str) -> None:
        path = self._resolve(key)
        try:
            path.unlink()
        except FileNotFoundError:
            pass  # idempotent
        except OSError as exc:
            raise StorageError(f"Failed to delete object '{key}'") from exc

    def _exists_sync(self, key: str) -> bool:
        return self._resolve(key).is_file()

    # -- references ---------------------------------------------------------
    def url(self, key: str) -> str:
        validate_object_key(key)
        # Provider-native reference. Not mounted publicly — the application
        # serves media through the controlled /api/media/{id}/file route.
        return f"/media/{key}"