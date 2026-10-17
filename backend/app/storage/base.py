"""Storage abstraction.

Application code must never depend on boto3 or the filesystem directly —
everything goes through `StorageProvider`. The abstraction implemented here
is the single seam between the media service and the concrete providers
(local disk, S3-compatible object storage).
"""

from __future__ import annotations

import re
from abc import ABC, abstractmethod


class StorageError(Exception):
    """Raised for any provider-level failure.

    Intentionally infrastructure-level: never serialised into API responses
    directly and never carries credentials or raw connection strings.
    """


class StorageObjectNotFoundError(StorageError):
    """Raised when a stored object does not exist for a given key."""


class InvalidKeyError(StorageError):
    """Raised when an object key is unsafe or ill-formed."""


# Object keys are always relative POSIX-style paths using only safe characters.
_SAFE_KEY_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._/-]*$")
_MAX_KEY_LENGTH = 512


def validate_object_key(key: str) -> None:
    """Reject anything that is not a safe, relative object key.

    Guards against path traversal (``../``, absolute paths, NUL bytes,
    empty/`.` segments and Windows separators). Uploaded filenames must never
    flow into keys — see `app.modules.media.service._build_keys`.
    """
    if not isinstance(key, str) or not key:
        raise InvalidKeyError("Object key must be a non-empty string")
    if "\x00" in key:
        raise InvalidKeyError("Object key must not contain NUL bytes")
    if len(key) > _MAX_KEY_LENGTH:
        raise InvalidKeyError("Object key is too long")
    if key.startswith("/") or "\\" in key:
        raise InvalidKeyError("Object key must be a relative POSIX path")
    if not _SAFE_KEY_RE.fullmatch(key):
        raise InvalidKeyError("Object key contains unsafe characters")
    for segment in key.split("/"):
        if segment in ("", ".", ".."):
            raise InvalidKeyError("Object key must not contain empty or dot segments")


class StorageProvider(ABC):
    """Interface every storage backend implements.

    All operations are async; providers wrap blocking I/O (filesystem, boto3)
    with ``asyncio.to_thread`` so the event loop is never blocked.
    """

    @property
    @abstractmethod
    def mode(self) -> str:
        """Storage mode identifier, e.g. ``"local"`` or ``"s3"``."""

    @abstractmethod
    async def put(
        self,
        key: str,
        data: bytes,
        content_type: str = "application/octet-stream",
    ) -> None:
        """Store ``data`` under ``key`` (overwrites an existing object)."""

    @abstractmethod
    async def get(self, key: str) -> bytes:
        """Return the stored object's bytes.

        Raises `StorageObjectNotFoundError` when the object does not exist and
        `StorageError` on other failures.
        """

    @abstractmethod
    async def delete(self, key: str) -> None:
        """Delete the object. Idempotent: missing objects are a no-op."""

    @abstractmethod
    async def exists(self, key: str) -> bool:
        """Return whether an object exists under ``key``."""

    @abstractmethod
    def url(self, key: str) -> str:
        """Return a storage-level URL/reference for an object.

        This does NOT expose credentials. The media service currently serves
        files through a controlled application route for every mode; these
        references exist so a future phase can switch to direct/pre-signed
        serving without changing callers.
        """