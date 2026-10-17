"""Media API tests: upload, listing, retrieval, file serving, deletion,
authentication/RBAC/CSRF, validation failures, de-duplication and cleanup.

Storage is the real LocalStorageProvider pointed at the isolated test
directory configured in conftest; the `client` fixture wipes it and the media
collection before every test.
"""

from __future__ import annotations

import io
import struct
import zlib
from pathlib import Path

import pytest
from PIL import Image

from app.core.config import get_settings
from app.db.mongo import get_mongo
from app.models.admin import Role
from app.modules.media import repository as media_repository
from app.storage import get_storage_provider
from app.storage.base import StorageError


# --------------------------------------------------------------------------
# helpers
# --------------------------------------------------------------------------
def _jpeg_bytes(width=600, height=400, color="crimson") -> bytes:
    buf = io.BytesIO()
    Image.new("RGB", (width, height), color).save(buf, "JPEG")
    return buf.getvalue()


def _png_bytes(width=64, height=48) -> bytes:
    buf = io.BytesIO()
    Image.new("RGB", (width, height), "blue").save(buf, "PNG")
    return buf.getvalue()


def _huge_png_header() -> bytes:
    sig = b"\x89PNG\r\n\x1a\n"

    def _chunk(typ, payload):
        return (
            struct.pack(">I", len(payload))
            + typ
            + payload
            + struct.pack(">I", zlib.crc32(typ + payload) & 0xFFFFFFFF)
        )

    ihdr = _chunk(b"IHDR", struct.pack(">IIBBBBB", 50000, 50000, 8, 2, 0, 0, 0))
    iend = _chunk(b"IEND", b"")
    return sig + ihdr + iend


async def _login_admin(client, make_admin, login, fetch_csrf, email="owner@example.com",
                       role=Role.OWNER) -> str:
    await make_admin(email, role=role)
    res = await login(email, "CorrectHorse!Battery9")
    assert res.status_code == 200, res.text
    return await fetch_csrf()


def _upload(client, token, data, filename="pixel.png", content_type="image/png"):
    return client.post(
        "/api/media",
        files={"file": (filename, data, content_type)},
        headers={"X-CSRF-Token": token},
    )


def _delete(client, token, media_id):
    return client.delete(
        f"/api/media/{media_id}", headers={"X-CSRF-Token": token}
    )


def _stored_files() -> list[Path]:
    root = Path(get_settings().STORAGE_LOCAL_DIR)
    if not root.exists():
        return []
    return [p for p in root.rglob("*") if p.is_file()]


async def _media_count() -> int:
    return await get_mongo().database["media"].count_documents({})


# --------------------------------------------------------------------------
# upload: happy path
# --------------------------------------------------------------------------
async def test_upload_creates_variants_and_metadata(client, make_admin, login, fetch_csrf):
    token = await _login_admin(client, make_admin, login, fetch_csrf)

    res = await _upload(client, token, _jpeg_bytes(600, 400), filename="hero.jpg")
    assert res.status_code == 201, res.text
    body = res.json()

    assert body["media_type"] == "image"
    assert body["format"] == "jpeg"
    assert body["mime_type"] == "image/jpeg"
    assert body["width"] == 600 and body["height"] == 400
    assert len(body["checksum"]) == 64
    assert body["storage_mode"] == "local"
    assert body["original_name"] == "hero.jpg"
    assert body["created_by"]
    assert len(body["variants"]) == 4
    names = {v["name"] for v in body["variants"]}
    assert names == {"original", "thumb", "md", "lg"}
    for variant in body["variants"]:
        assert variant["mime_type"] == "image/webp"
        assert variant["object_key"].startswith("media/")
    assert set(body["urls"].keys()) == names
    for url in body["urls"].values():
        assert url.startswith("/api/media/")
        assert "file?variant=" in url
    # no storage internals leak into responses
    raw = res.text.lower()
    assert "aws" not in raw
    assert "secret" not in raw
    assert "access_key" not in raw
    assert "storage-local" not in raw
    assert await _media_count() == 1


async def test_upload_accepts_mismatched_extension_and_content_type(
    client, make_admin, login, fetch_csrf
):
    token = await _login_admin(client, make_admin, login, fetch_csrf)
    res = await _upload(
        client,
        token,
        _png_bytes(),
        filename="totally-not-a-jpg.jpg",
        content_type="application/octet-stream",
    )
    assert res.status_code == 201, res.text
    assert res.json()["format"] == "png"


async def test_upload_duplicate_reuses_existing_media(
    client, make_admin, login, fetch_csrf
):
    token = await _login_admin(client, make_admin, login, fetch_csrf)
    first = await _upload(client, token, _jpeg_bytes())
    assert first.status_code == 201
    first_id = first.json()["id"]
    files_after_first = len(_stored_files())
    assert files_after_first == 4

    second = await _upload(client, token, _jpeg_bytes())
    assert second.status_code == 200  # de-duplicated, not created
    assert second.json()["id"] == first_id
    assert await _media_count() == 1
    assert len(_stored_files()) == files_after_first  # nothing new stored


# --------------------------------------------------------------------------
# upload: authentication / authorization / CSRF
# --------------------------------------------------------------------------
async def test_upload_without_authentication_rejected(client, fetch_csrf):
    token = await fetch_csrf()  # CSRF passes; auth must still fail
    res = await _upload(client, token, _jpeg_bytes())
    assert res.status_code == 401
    assert res.json()["error"]["code"] == "NOT_AUTHENTICATED"


async def test_upload_without_csrf_rejected(client, make_admin, login, fetch_csrf):
    token = await _login_admin(client, make_admin, login, fetch_csrf)
    res = await client.post(
        "/api/media", files={"file": ("a.png", _png_bytes(), "image/png")}
    )
    assert res.status_code == 403
    assert res.json()["error"]["code"] == "CSRF_MISSING"


async def test_upload_with_bad_csrf_rejected(client, make_admin, login, fetch_csrf):
    await _login_admin(client, make_admin, login, fetch_csrf)
    res = await client.post(
        "/api/media",
        files={"file": ("a.png", _png_bytes(), "image/png")},
        headers={"X-CSRF-Token": "definitely-wrong"},
    )
    assert res.status_code == 403
    assert res.json()["error"]["code"] == "CSRF_INVALID"


async def test_editor_can_upload(client, make_admin, login, fetch_csrf):
    token = await _login_admin(
        client, make_admin, login, fetch_csrf, email="editor@example.com", role=Role.EDITOR
    )
    res = await _upload(client, token, _png_bytes())
    assert res.status_code == 201, res.text


# --------------------------------------------------------------------------
# upload: validation failures
# --------------------------------------------------------------------------
async def test_upload_rejects_renamed_text_file(client, make_admin, login, fetch_csrf):
    token = await _login_admin(client, make_admin, login, fetch_csrf)
    res = await _upload(
        client, token, b"not an image at all " * 50, filename="image.jpg",
        content_type="image/jpeg",
    )
    assert res.status_code == 415
    assert res.json()["error"]["code"] == "UNSUPPORTED_MEDIA_TYPE"
    assert await _media_count() == 0


async def test_upload_rejects_corrupt_image(client, make_admin, login, fetch_csrf):
    token = await _login_admin(client, make_admin, login, fetch_csrf)
    res = await _upload(
        client, token, _jpeg_bytes(800, 600)[:60], filename="broken.jpg"
    )
    assert res.status_code == 422
    assert res.json()["error"]["code"] == "INVALID_IMAGE"
    assert await _media_count() == 0


async def test_upload_rejects_oversized_file(client, make_admin, login, fetch_csrf):
    token = await _login_admin(client, make_admin, login, fetch_csrf)
    limit = get_settings().PRODUCT_IMAGE_MAX_BYTES
    res = await _upload(client, token, b"\x00" * (limit + 1))
    assert res.status_code == 413
    assert res.json()["error"]["code"] == "FILE_TOO_LARGE"
    assert await _media_count() == 0


async def test_upload_rejects_decompression_bomb(client, make_admin, login, fetch_csrf):
    token = await _login_admin(client, make_admin, login, fetch_csrf)
    res = await _upload(client, token, _huge_png_header(), filename="bomb.png")
    assert res.status_code == 422
    assert res.json()["error"]["code"] == "IMAGE_TOO_LARGE"
    assert await _media_count() == 0


async def test_upload_rejects_unsupported_format(client, make_admin, login, fetch_csrf):
    token = await _login_admin(client, make_admin, login, fetch_csrf)
    gif = b"GIF89a" + b"\x00" * 64
    res = await _upload(client, token, gif, filename="anim.gif", content_type="image/gif")
    assert res.status_code == 415
    assert res.json()["error"]["code"] == "UNSUPPORTED_MEDIA_TYPE"


# --------------------------------------------------------------------------
# listing + retrieval
# --------------------------------------------------------------------------
async def _upload_three(client, token):
    colors = ["red", "green", "blue"]
    for color in colors:
        buf = io.BytesIO()
        Image.new("RGB", (80, 60), color).save(buf, "JPEG")
        res = await _upload(client, token, buf.getvalue(), filename=f"{color}.jpg")
        assert res.status_code == 201, res.text


async def test_listing_pagination_and_sort(client, make_admin, login, fetch_csrf):
    token = await _login_admin(client, make_admin, login, fetch_csrf)
    await _upload_three(client, token)

    res = await client.get("/api/media?page=1&page_size=2")
    assert res.status_code == 200
    body = res.json()
    assert body["total"] == 3
    assert body["page"] == 1
    assert body["page_size"] == 2
    assert body["pages"] == 2
    assert len(body["items"]) == 2

    # newest-first: last uploaded appears first
    assert body["items"][0]["original_name"] == "blue.jpg"

    page2 = (await client.get("/api/media?page=2&page_size=2")).json()
    assert len(page2["items"]) == 1
    assert page2["items"][0]["original_name"] == "red.jpg"

    oldest = (await client.get("/api/media?page=1&page_size=3&sort=oldest")).json()
    assert oldest["items"][0]["original_name"] == "red.jpg"


async def test_listing_requires_authentication(client):
    res = await client.get("/api/media")
    assert res.status_code == 401


async def test_single_media_retrieval(client, make_admin, login, fetch_csrf):
    token = await _login_admin(client, make_admin, login, fetch_csrf)
    created = (await _upload(client, token, _png_bytes(), filename="logo.png")).json()

    res = await client.get(f"/api/media/{created['id']}")
    assert res.status_code == 200
    assert res.json()["id"] == created["id"]
    assert res.json()["checksum"] == created["checksum"]

    missing = await client.get("/api/media/000000000000000000000000")
    assert missing.status_code == 404
    assert missing.json()["error"]["code"] == "MEDIA_NOT_FOUND"


# --------------------------------------------------------------------------
# file serving
# --------------------------------------------------------------------------
async def test_file_endpoint_serves_stored_webp(client, make_admin, login, fetch_csrf):
    token = await _login_admin(client, make_admin, login, fetch_csrf)
    created = (await _upload(client, token, _png_bytes())).json()

    res = await client.get(f"/api/media/{created['id']}/file?variant=original")
    assert res.status_code == 200
    assert res.headers["content-type"] == "image/webp"
    assert res.content[:4] == b"RIFF"
    assert res.content[8:12] == b"WEBP"

    for variant in ("thumb", "md", "lg"):
        r = await client.get(f"/api/media/{created['id']}/file?variant={variant}")
        assert r.status_code == 200
        assert r.content[:4] == b"RIFF"


async def test_file_endpoint_rejects_unknown_variant(client, make_admin, login, fetch_csrf):
    token = await _login_admin(client, make_admin, login, fetch_csrf)
    created = (await _upload(client, token, _png_bytes())).json()
    res = await client.get(
        f"/api/media/{created['id']}/file?variant=../../etc/passwd"
    )
    assert res.status_code == 404
    assert res.json()["error"]["code"] == "INVALID_VARIANT"


async def test_file_endpoint_404_when_object_missing(client, make_admin, login, fetch_csrf):
    token = await _login_admin(client, make_admin, login, fetch_csrf)
    created = (await _upload(client, token, _png_bytes())).json()

    provider = get_storage_provider()
    original_key = created["variants"][0]["object_key"]
    await provider.delete(original_key)  # simulate a lost object

    res = await client.get(f"/api/media/{created['id']}/file?variant=original")
    assert res.status_code == 404
    assert res.json()["error"]["code"] == "MEDIA_FILE_NOT_FOUND"


# --------------------------------------------------------------------------
# deletion
# --------------------------------------------------------------------------
async def test_delete_removes_objects_documents_and_files(
    client, make_admin, login, fetch_csrf
):
    token = await _login_admin(client, make_admin, login, fetch_csrf)
    created = (await _upload(client, token, _png_bytes())).json()
    assert len(_stored_files()) == 4

    res = await _delete(client, token, created["id"])
    assert res.status_code == 200
    assert res.json() == {"status": "ok"}
    assert await _media_count() == 0
    assert _stored_files() == []


async def test_admin_role_can_delete(client, make_admin, login, fetch_csrf):
    token = await _login_admin(
        client, make_admin, login, fetch_csrf, email="admin@example.com", role=Role.ADMIN
    )
    created = (await _upload(client, token, _png_bytes())).json()
    res = await _delete(client, token, created["id"])
    assert res.status_code == 200


async def test_editor_cannot_delete(client, make_admin, login, fetch_csrf):
    token = await _login_admin(
        client, make_admin, login, fetch_csrf, email="editor@example.com", role=Role.EDITOR
    )
    created = (await _upload(client, token, _png_bytes())).json()
    res = await _delete(client, token, created["id"])
    assert res.status_code == 403
    assert res.json()["error"]["code"] == "INSUFFICIENT_ROLE"
    assert await _media_count() == 1  # record kept


async def test_delete_missing_media(client, make_admin, login, fetch_csrf):
    token = await _login_admin(client, make_admin, login, fetch_csrf)
    res = await _delete(client, token, "000000000000000000000000")
    assert res.status_code == 404
    assert res.json()["error"]["code"] == "MEDIA_NOT_FOUND"


async def test_delete_requires_csrf(client, make_admin, login, fetch_csrf):
    token = await _login_admin(client, make_admin, login, fetch_csrf)
    created = (await _upload(client, token, _png_bytes())).json()
    res = await client.delete(f"/api/media/{created['id']}")
    assert res.status_code == 403
    assert res.json()["error"]["code"] == "CSRF_MISSING"


# --------------------------------------------------------------------------
# cleanup + failure behaviour
# --------------------------------------------------------------------------
class _PartialPutProvider:
    """Fake provider: first put succeeds, subsequent puts blow up."""

    mode = "local"

    def __init__(self):
        self.put_calls = 0
        self.deleted: list[str] = []

    async def put(self, key, data, content_type="application/octet-stream"):
        self.put_calls += 1
        if self.put_calls == 1:
            return
        raise StorageError("disk full")

    async def get(self, key):
        raise StorageError("nope")

    async def exists(self, key):
        return True

    async def delete(self, key):
        self.deleted.append(key)

    def url(self, key):
        return "/media/" + key


async def test_upload_cleans_up_when_storage_fails_partway(
    client, make_admin, login, fetch_csrf, monkeypatch
):
    token = await _login_admin(client, make_admin, login, fetch_csrf)
    failing = _PartialPutProvider()
    monkeypatch.setattr("app.modules.media.service.get_storage_provider", lambda: failing)

    res = await _upload(client, token, _jpeg_bytes())
    assert res.status_code == 500
    assert res.json()["error"]["code"] == "STORAGE_ERROR"
    # the single stored variant was cleaned up and no document was created
    assert failing.put_calls == 2
    assert len(failing.deleted) == 1
    assert failing.deleted[0].endswith("/original.webp")
    assert await _media_count() == 0


async def test_upload_cleans_up_when_db_insert_fails(
    client, make_admin, login, fetch_csrf, monkeypatch
):
    token = await _login_admin(client, make_admin, login, fetch_csrf)
    real_provider = get_storage_provider()

    async def boom(*args, **kwargs):
        raise RuntimeError("db down")

    monkeypatch.setattr(media_repository, "insert_media", boom)
    monkeypatch.setattr("app.modules.media.service.get_storage_provider", lambda: real_provider)

    res = await _upload(client, token, _png_bytes())
    assert res.status_code == 500
    assert res.json()["error"]["code"] == "MEDIA_CREATE_FAILED"
    assert _stored_files() == []  # no orphaned objects
    assert await _media_count() == 0


class _FailingDeleteProvider(_PartialPutProvider):
    async def delete(self, key):
        raise StorageError("delete failed")


async def test_delete_keeps_record_when_storage_delete_fails(
    client, make_admin, login, fetch_csrf, monkeypatch
):
    token = await _login_admin(client, make_admin, login, fetch_csrf)
    created = (await _upload(client, token, _png_bytes())).json()

    failing = _FailingDeleteProvider()
    monkeypatch.setattr("app.modules.media.service.get_storage_provider", lambda: failing)

    res = await _delete(client, token, created["id"])
    assert res.status_code == 500
    assert res.json()["error"]["code"] == "STORAGE_DELETE_FAILED"
    # document preserved so a retry can converge
    assert await _media_count() == 1
    assert (await client.get(f"/api/media/{created['id']}")).status_code == 200


async def test_failed_upload_leaves_no_partial_media(client, make_admin, login, fetch_csrf):
    token = await _login_admin(client, make_admin, login, fetch_csrf)
    res = await _upload(client, token, b"\x00" * (get_settings().PRODUCT_IMAGE_MAX_BYTES + 1))
    assert res.status_code == 413
    assert _stored_files() == []
    assert await _media_count() == 0