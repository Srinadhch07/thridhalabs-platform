"""Public media delivery tests (`/api/public/media/{id}`).

Verifies the unauthenticated, read-only variant endpoint: success with cache
headers, invalid/unknown ids, arbitrary variant/key rejection, method
restrictions, and that the admin route still requires authentication.
"""

# ---------------------------------------------------------------------------
# Helpers (mirror test_media_api.py conventions)
# ---------------------------------------------------------------------------
import io

from PIL import Image

from app.core.config import get_settings


def _png_bytes(width: int = 64, height: int = 48) -> bytes:
    buf = io.BytesIO()
    Image.new("RGB", (width, height), "blue").save(buf, "PNG")
    return buf.getvalue()


async def _upload(client, make_admin, login, fetch_csrf) -> str:
    await make_admin("owner@example.com")
    await login("owner@example.com", "CorrectHorse!Battery9")
    csrf = await fetch_csrf()
    upload = await client.post(
        "/api/media",
        files={"file": ("pixel.png", _png_bytes(), "image/png")},
        headers={"X-CSRF-Token": csrf},
    )
    assert upload.status_code in (200, 201), upload.text
    return upload.json()["id"]


async def test_public_media_serves_variant_without_auth(client, make_admin, login, fetch_csrf):
    media_id = await _upload(client, make_admin, login, fetch_csrf)
    res = await client.get(f"/api/public/media/{media_id}")
    assert res.status_code == 200
    assert res.headers["content-type"].startswith("image/")
    assert res.headers["cache-control"] == "public, max-age=31536000, immutable"

    res_md = await client.get(f"/api/public/media/{media_id}?variant=md")
    assert res_md.status_code == 200
    assert res.headers["cache-control"] == res_md.headers["cache-control"]

    res_thumb = await client.get(f"/api/public/media/{media_id}?variant=thumb")
    assert res_thumb.status_code == 200
    # All variants are transcoded to WebP.
    assert res.headers["content-type"] == "image/webp"


async def test_public_media_unknown_id_404(client):
    res = await client.get("/api/public/media/0123456789abcdef01234567")
    assert res.status_code == 404


async def test_public_media_invalid_id_404(client):
    res = await client.get("/api/public/media/../..")
    assert res.status_code in (404, 422)

    res = await client.get("/api/public/media/not-an-object-id")
    assert res.status_code == 404


async def test_public_media_rejects_arbitrary_variant(client, make_admin, login, fetch_csrf):
    media_id = await _upload(client, make_admin, login, fetch_csrf)
    res = await client.get(f"/api/public/media/{media_id}?variant=../../etc/passwd")
    assert res.status_code in (404, 422)

    res = await client.get(f"/api/public/media/{media_id}?variant=original/../../secret")
    assert res.status_code in (404, 422)


async def test_public_media_get_only(client, make_admin, login, fetch_csrf):
    media_id = await _upload(client, make_admin, login, fetch_csrf)
    assert (await client.post(f"/api/public/media/{media_id}")).status_code == 405
    assert (await client.delete(f"/api/public/media/{media_id}")).status_code == 405


async def test_admin_media_file_route_still_requires_auth(client, make_admin, login, fetch_csrf):
    media_id = await _upload(client, make_admin, login, fetch_csrf)
    client.cookies.clear()
    res = await client.get(f"/api/media/{media_id}/file")
    assert res.status_code == 401

    res = await client.get(f"/api/media/{media_id}/file?variant=md")
    assert res.status_code == 401


async def test_public_media_uses_no_secret_values(client):
    res = await client.get("/api/public/media/0123456789abcdef01234567")
    body = res.text
    assert get_settings().AWS_SECRET_ACCESS_KEY is None or (
        get_settings().AWS_SECRET_ACCESS_KEY.get_secret_value() not in body
    )