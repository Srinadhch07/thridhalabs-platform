"""LocalStorageProvider unit tests — no database or HTTP server involved."""

from __future__ import annotations

import pytest

from app.storage.base import (
    InvalidKeyError,
    StorageObjectNotFoundError,
    validate_object_key,
)
from app.storage.local import LocalStorageProvider

KEY = "media/2026/10/0123abc/original.webp"


@pytest.fixture
def local(tmp_path):
    return LocalStorageProvider(tmp_path)


async def test_put_get_roundtrip(local):
    await local.put(KEY, b"hello-image")
    assert await local.exists(KEY)
    assert await local.get(KEY) == b"hello-image"


async def test_put_creates_parent_directories(local, tmp_path):
    await local.put(KEY, b"data")
    assert (tmp_path / "media" / "2026" / "10" / "0123abc" / "original.webp").exists()


async def test_put_overwrites_existing(local):
    await local.put(KEY, b"first")
    await local.put(KEY, b"second")
    assert await local.get(KEY) == b"second"


async def test_put_with_content_type_is_ignored_for_local(local):
    await local.put(KEY, b"data", content_type="image/webp")
    assert await local.get(KEY) == b"data"


async def test_get_missing_raises(local):
    with pytest.raises(StorageObjectNotFoundError):
        await local.get("media/missing.webp")


async def test_exists_missing_is_false(local):
    assert not await local.exists("media/missing.webp")


async def test_delete_removes_object(local):
    await local.put(KEY, b"data")
    await local.delete(KEY)
    assert not await local.exists(KEY)


async def test_delete_missing_is_idempotent(local):
    await local.delete("media/never-existed.webp")  # no exception


async def test_files_never_escape_root(local, tmp_path):
    await local.put(KEY, b"data")
    escaped = tmp_path / "media"  # key root actually lives under tmp_path/media
    assert (escaped / "2026" / "10" / "0123abc" / "original.webp").read_bytes() == b"data"


async def test_url_is_relative_and_safe(local):
    url = local.url(KEY)
    assert url == f"/media/{KEY}"
    assert not url.startswith("/../")
    assert "\\" not in url


@pytest.mark.parametrize(
    "key",
    [
        "../escape.txt",
        "media/../../etc/passwd",
        "media/./x.webp",
        "media//x.webp",
        "/absolute/path.webp",
        r"media\..\windows",
        "..",
        ".",
        "",
        None,
        "a\x00b",
        "media/..",
        ".hidden",
    ],
)
async def test_unsafe_keys_rejected_by_validation(local, key):
    with pytest.raises(InvalidKeyError):
        validate_object_key(key)
    with pytest.raises(InvalidKeyError):
        await local.put(key, b"data")
    with pytest.raises(InvalidKeyError):
        await local.get(key)
    with pytest.raises(InvalidKeyError):
        await local.url(key)


async def test_generated_style_keys_are_accepted(local):
    validate_object_key(KEY)
    validate_object_key("media/2026/10/deadbeef/thumb.webp")
    validate_object_key("media/2026/10/deadbeef/lg.webp")


async def test_long_key_rejected(local):
    with pytest.raises(InvalidKeyError):
        validate_object_key("media/" + "a" * 600)