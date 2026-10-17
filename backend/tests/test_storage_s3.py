"""S3StorageProvider unit tests with a fully mocked boto3 client.

No real AWS credentials or network traffic are used — the provider is driven
against `unittest.mock` objects, so nothing is ever sent to a real bucket.
"""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest
from botocore.exceptions import ClientError

from app.storage.base import (
    InvalidKeyError,
    StorageError,
    StorageObjectNotFoundError,
)
from app.storage.s3 import S3StorageProvider

KEY = "media/2026/10/0123abc/original.webp"


def _client_error(code: str, operation: str = "GetObject") -> ClientError:
    return ClientError(
        {
            "Error": {"Code": code, "Message": "boom"},
            "ResponseMetadata": {
                "RequestId": "req-123",
                "HTTPStatusCode": 404 if code in ("404", "NotFound", "NoSuchKey") else 500,
            },
        },
        operation,
    )


@pytest.fixture
def s3():
    client = MagicMock()
    provider = S3StorageProvider(
        region="us-east-1",
        bucket="test-bucket",
        access_key="AKIDTEST",
        secret_key="test-secret-value",
    )
    provider._client = client  # inject mock before any lazy creation
    return provider, client


async def test_put_calls_put_object(s3):
    provider, client = s3
    await provider.put(KEY, b"data", content_type="image/webp")
    client.put_object.assert_called_once_with(
        Bucket="test-bucket", Key=KEY, Body=b"data", ContentType="image/webp"
    )


async def test_get_returns_body_bytes(s3):
    provider, client = s3
    client.get_object.return_value = {"Body": MagicMock(**{"read.return_value": b"data"})}
    assert await provider.get(KEY) == b"data"
    client.get_object.assert_called_once_with(Bucket="test-bucket", Key=KEY)


async def test_get_not_found_maps_to_storage_object_not_found(s3):
    provider, client = s3
    client.get_object.side_effect = _client_error("NoSuchKey")
    with pytest.raises(StorageObjectNotFoundError):
        await provider.get(KEY)


async def test_exists_true_when_head_succeeds(s3):
    provider, client = s3
    client.head_object.return_value = {"ContentLength": 4}
    assert await provider.exists(KEY) is True


async def test_exists_false_on_404(s3):
    provider, client = s3
    client.head_object.side_effect = _client_error("404")
    assert await provider.exists(KEY) is False


async def test_exists_raises_on_other_errors(s3):
    provider, client = s3
    client.head_object.side_effect = _client_error("InternalError", "HeadObject")
    with pytest.raises(StorageError):
        await provider.exists(KEY)


async def test_delete_calls_delete_object(s3):
    provider, client = s3
    await provider.delete(KEY)
    client.delete_object.assert_called_once_with(Bucket="test-bucket", Key=KEY)


async def test_url_generates_presigned_url(s3):
    provider, client = s3
    client.generate_presigned_url.return_value = "https://test-bucket.s3.amazonaws.com/signed"
    url = provider.url(KEY)
    assert url == "https://test-bucket.s3.amazonaws.com/signed"
    client.generate_presigned_url.assert_called_once()
    params = client.generate_presigned_url.call_args
    assert params.args[0] == "get_object"
    assert params.kwargs["Params"] == {"Bucket": "test-bucket", "Key": KEY}


async def test_storage_error_never_leaks_credentials(s3):
    provider, client = s3
    client.put_object.side_effect = _client_error("InternalError", "PutObject")
    with pytest.raises(StorageError) as excinfo:
        await provider.put(KEY, b"data")
    assert "test-secret-value" not in str(excinfo.value)
    assert "AKIDTEST" not in str(excinfo.value)


async def test_unsafe_key_rejected_before_network(s3):
    provider, client = s3
    with pytest.raises(InvalidKeyError):
        await provider.put("../../etc/passwd", b"x")
    client.put_object.assert_not_called()


def test_missing_configuration_rejected():
    with pytest.raises(ValueError):
        S3StorageProvider(region="", bucket="b", access_key="a", secret_key="s")
    with pytest.raises(ValueError):
        S3StorageProvider(region="r", bucket="", access_key="a", secret_key="s")
    with pytest.raises(ValueError):
        S3StorageProvider(region="r", bucket="b", access_key="", secret_key="s")


def test_provider_does_not_repr_secrets():
    provider = S3StorageProvider(
        region="us-east-1",
        bucket="test-bucket",
        access_key="AKIDTOP-SECRET",
        secret_key="super-secret-value-xyz",
    )
    assert "super-secret-value-xyz" not in repr(provider)
    assert "AKIDTOP-SECRET" not in repr(provider)


def test_url_rejects_unsafe_key(s3):
    provider, _client = s3
    with pytest.raises(InvalidKeyError):
        provider.url("../../escape")