"""Testimonials API tests: CRUD, publishing/featured gating, client & media
references, pagination/sorting, public visibility, RBAC/CSRF."""

from __future__ import annotations

from app.models.admin import Role

from tests._content_helpers import (
    create_client,
    create_testimonial,
    login_admin,
    upload_media,
)


async def test_create_defaults(client, make_admin, fetch_csrf):
    token = await login_admin(client, make_admin, fetch_csrf)
    created = await create_testimonial(client, token, person_name="Ada Lovelace")
    assert created["person_name"] == "Ada Lovelace"
    assert created["published"] is False
    assert created["featured"] is False
    assert created["display_order"] == 0


async def test_create_with_client_link_and_photo(client, make_admin, fetch_csrf):
    token = await login_admin(client, make_admin, fetch_csrf)
    client_doc = await create_client(client, token, name="Acme")
    media = await upload_media(client, token)
    created = await create_testimonial(
        client, token,
        person_name="Guy", role="CTO", company="Acme",
        client_id=client_doc["id"], profile_image_media_id=media["id"],
        published=True, featured=True, rating=5,
    )
    assert created["client"]["slug"] == "acme"
    assert created["client"]["name"] == "Acme"
    assert created["profile_image_media_id"] == media["id"]
    assert created["published"] is True


async def test_validation(client, make_admin, fetch_csrf):
    token = await login_admin(client, make_admin, fetch_csrf)
    cases = [
        {"person_name": "No text"},
        {"person_name": "X", "testimonial_text": "y", "rating": 6},
        {"person_name": "X", "testimonial_text": "y", "rating": -1},
        {"person_name": "X", "testimonial_text": "y", "client_id": "000000000000000000000000"},
        {"person_name": "X", "testimonial_text": "y", "photo_media_id": "000000000000000000000000"},
    ]
    for payload in cases:
        res = await client.post(
            "/api/testimonials", json=payload, headers={"X-CSRF-Token": token}
        )
        assert res.status_code in (400, 422), (payload, res.text)


async def test_list_pagination_and_sorting(client, make_admin, fetch_csrf):
    token = await login_admin(client, make_admin, fetch_csrf)
    await create_testimonial(client, token, person_name="A", display_order=1)
    await create_testimonial(client, token, person_name="B", display_order=0)
    await create_testimonial(client, token, person_name="C", display_order=2, published=True)

    r = await client.get("/api/testimonials?published=true")
    assert r.json()["total"] == 1 and r.json()["items"][0]["person_name"] == "C"
    r = await client.get("/api/testimonials?featured=true")
    assert r.json()["total"] == 0

    r = await client.get("/api/testimonials?sort=display_order&order=asc&page_size=2")
    assert [t["person_name"] for t in r.json()["items"]] == ["B", "A"]
    assert r.json()["total"] == 3

    bad = await client.get("/api/testimonials?sort=rating,__proto__")
    assert bad.status_code == 422


async def test_update_flows(client, make_admin, fetch_csrf):
    token = await login_admin(client, make_admin, fetch_csrf)
    created = await create_testimonial(client, token, person_name="Old")
    res = await client.patch(
        f"/api/testimonials/{created['id']}",
        json={"person_name": "New", "published": True, "featured": True},
        headers={"X-CSRF-Token": token},
    )
    body = res.json()
    assert body["person_name"] == "New"
    assert body["published"] is True and body["featured"] is True
    assert body["testimonial_text"] == "Great work."  # untouched

    res = await client.delete(f"/api/testimonials/{created['id']}")
    assert res.status_code == 403  # CSRF missing
    ok = await client.delete(f"/api/testimonials/{created['id']}", headers={"X-CSRF-Token": token})
    assert ok.status_code == 200
    assert (await client.get(f"/api/testimonials/{created['id']}")).status_code == 404


async def test_rbac(client, make_admin, fetch_csrf):
    token = await login_admin(client, make_admin, fetch_csrf, role=Role.EDITOR)
    created = await create_testimonial(client, token, person_name="Editable")
    res = await client.delete(f"/api/testimonials/{created['id']}", headers={"X-CSRF-Token": token})
    assert res.status_code == 403 and res.json()["error"]["code"] == "INSUFFICIENT_ROLE"


# --------------------------------------------------------------------------
# public API
# --------------------------------------------------------------------------
async def test_public_gates_unpublished(client, make_admin, fetch_csrf):
    token = await login_admin(client, make_admin, fetch_csrf)
    hidden = await create_testimonial(client, token, person_name="Hidden", testimonial_text="secret")
    shown = await create_testimonial(
        client, token, person_name="Shown", testimonial_text="public hi",
        published=True, featured=True, role="CEO", rating=5,
    )

    res = await client.get("/api/public/testimonials")
    assert res.status_code == 200
    items = res.json()["items"]
    assert len(items) == 1
    item = items[0]
    assert item["person_name"] == "Shown"
    assert item["rating"] == 5
    assert "testimonial_text" in item  # public key field is included

    single = await client.get(f"/api/public/testimonials/{shown['id']}")
    assert single.status_code == 200
    unpublished = await client.get(f"/api/public/testimonials/{hidden['id']}")
    assert unpublished.status_code == 404
    missing = await client.get(f"/api/public/testimonials/{'0' * 24}")
    assert missing.status_code == 404


async def test_public_ordering_featured_first(client, make_admin, fetch_csrf):
    token = await login_admin(client, make_admin, fetch_csrf)
    await create_testimonial(client, token, person_name="Plain A", display_order=0, published=True)
    await create_testimonial(client, token, person_name="Plain B", display_order=1, published=True)
    await create_testimonial(client, token, person_name="Star", display_order=0, published=True, featured=True)

    res = await client.get("/api/public/testimonials")
    names = [t["person_name"] for t in res.json()["items"]]
    assert names[0] == "Star"
    assert set(names[1:]) == {"Plain A", "Plain B"}


async def test_date_round_trips_as_iso_date_string(client, make_admin, fetch_csrf):
    """Regression: `date` is a date-only field — it must survive the Mongo
    round-trip as `YYYY-MM-DD` on create, fetch and patch."""
    token = await login_admin(client, make_admin, fetch_csrf)
    created = await create_testimonial(client, token, person_name="Dated", date="2026-05-22")
    assert created["date"] == "2026-05-22"

    fetched = await client.get(f"/api/testimonials/{created['id']}")
    assert fetched.status_code == 200
    assert fetched.json()["date"] == "2026-05-22"

    patched = await client.patch(
        f"/api/testimonials/{created['id']}",
        json={"date": "2026-05-23"},
        headers={"X-CSRF-Token": token},
    )
    assert patched.status_code == 200, patched.text
    assert patched.json()["date"] == "2026-05-23"