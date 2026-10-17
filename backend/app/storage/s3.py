"""S3-compatible object storage provider (boto3).

AWS credentials are read from application settings at factory time and passed
explicitly to boto3 — they are never logged, serialised, or included in API
responses or exceptions. The bucket is never made public: files are served
through the controlled application route, and `url()` returns pre-signed URLs
for any future direct-serving needs.
"""

from __future__ import annotations

import asyncio
from typing import Any

import boto3
from botocore.client import BaseClient
from botocore.exceptions import BotoCoreError, ClientError

from app.core.logging import get_logger
from app.storage.base import (
    StorageError,
    StorageObjectNotFoundError,
    StorageProvider,
    validate_object_key,
)

log = get_logger("storage.s3")

_PRESIGNED_URL_TTL_SECONDS = 3600
_OBJECT_NOT_FOUND_CODES = ("404", "NotFound", "NoSuchKey")


class S3StorageProvider(StorageProvider):
    """Stores objects in an S3-compatible bucket via boto3.

    Constructor arguments come only from validated settings; callers never see
    secrets. The boto3 client is created lazily (client construction performs
    no network I/O) and reused for the lifetime of the provider.
    """

    def __init__(
        self,
        *,
        region: str,
        bucket: str,
        access_key: str,
        secret_key: str,
    ) -> None:
        if not region or not bucket or not access_key or not secret_key:
            raise ValueError("S3 storage requires region, bucket and credentials")
        self._region = region
        self._bucket = bucket
        self._access_key = access_key
        self._secret_key = secret_key
        self._client: BaseClient | None = None

    @property
    def mode(self) -> str:
        return "s3"

    def _get_client(self) -> BaseClient:
        if self._client is None:
            self._client = boto3.client(
                "s3",
                region_name=self._region,
                aws_access_key_id=self._access_key,
                aws_secret_access_key=self._secret_key,
            )
        return self._client

    @staticmethod
    def _error_code(exc: ClientError) -> str:
        return str(exc.response.get("Error", {}).get("Code", "ClientError"))

    def _wrap_not_found(self, exc: ClientError, key: str) -> StorageError:
        if self._error_code(exc) in _OBJECT_NOT_FOUND_CODES:
            return StorageObjectNotFoundError(f"Object not found: '{key}'")
        return StorageError(f"Storage failure for object '{key}'")

    # -- ops ----------------------------------------------------------------
    async def put(
        self,
        key: str,
        data: bytes,
        content_type: str = "application/octet-stream",
    ) -> None:
        validate_object_key(key)

        def _do() -> None:
            try:
                self._get_client().put_object(
                    Bucket=self._bucket,
                    Key=key,
                    Body=data,
                    ContentType=content_type,
                )
            except ClientError as exc:
                raise StorageError(
                    f"Storage failure for object '{key}' ({self._error_code(exc)})"
                ) from exc
            except BotoCoreError as exc:
                raise StorageError(f"Storage failure for object '{key}'") from exc

        await asyncio.to_thread(_do)

    async def get(self, key: str) -> bytes:
        validate_object_key(key)

        def _do() -> bytes:
            try:
                response = self._get_client().get_object(
                    Bucket=self._bucket, Key=key
                )
                body = response.get("Body")
                if body is None:
                    raise StorageError(f"Empty response body for '{key}'")
                return body.read()
            except ClientError as exc:
                raise self._wrap_not_found(exc, key) from exc
            except BotoCoreError as exc:
                raise StorageError(f"Storage failure for object '{key}'") from exc

        return await asyncio.to_thread(_do)

    async def delete(self, key: str) -> None:
        validate_object_key(key)

        def _do() -> None:
            try:
                self._get_client().delete_object(Bucket=self._bucket, Key=key)
            except ClientError as exc:
                raise StorageError(
                    f"Storage failure for object '{key}' ({self._error_code(exc)})"
                ) from exc
            except BotoCoreError as exc:
                raise StorageError(f"Storage failure for object '{key}'") from exc

        await asyncio.to_thread(_do)

    async def exists(self, key: str) -> bool:
        validate_object_key(key)

        def _do() -> bool:
            try:
                self._get_client().head_object(Bucket=self._bucket, Key=key)
                return True
            except ClientError as exc:
                if self._error_code(exc) in _OBJECT_NOT_FOUND_CODES:
                    return False
                raise StorageError(
                    f"Storage failure for object '{key}' ({self._error_code(exc)})"
                ) from exc
            except BotoCoreError as exc:
                raise StorageError(f"Storage failure for object '{key}'") from exc

        return await asyncio.to_thread(_do)

    # -- references ---------------------------------------------------------
    def url(self, key: str) -> str:
        validate_object_key(key)
        return self._get_client().generate_presigned_url(
            "get_object",
            Params={"Bucket": self._bucket, "Key": key},
            ExpiresIn=_PRESIGNED_URL_TTL_SECONDS,
        )