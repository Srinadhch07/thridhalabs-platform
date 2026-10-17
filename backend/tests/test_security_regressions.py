"""Security regression tests (Phase 4 audit, SCRUTINY.md SEC-001/002).

Locks in invariants identified during the security audit so future changes
cannot silently regress them:

- public submission field caps and moderation invariance,
- controlled 404s for malformed/unknown public ids,
- CSRF-before-auth ordering on admin deletes,
- the login rate limiter keys on the request socket address (SEC-001) and
  does not trust `X-Forwarded-For` — this pins the current behaviour and must
  be updated when proxy-aware limiting lands.
"""

from __future__ import annotations

from app.core.config import get_settings
from app.db.mongo import get_mongo


async def test_public_testimonial_malformed_and_unknown_ids_return_404(client):
    for bad in ("not-an-object-id", "0123456789abcdef01234567"):
        res = await client.get(f"/api/public/testimonials/{bad}")
        assert res.status_code == 404, (bad, res.status_code, res.text)
        assert res.json()["error"]["code"] == "TESTIMONIAL_NOT_FOUND"


async def test_public_submit_field_limits_enforced_and_not_stored(client):
    long_text = "x" * 5001
    cases = [
        {"testimonial_text": "valid"},  # missing person_name
        {"person_name": "   ", "testimonial_text": "valid"},  # blank name
        {"person_name": "Valid", "testimonial_text": "   "},  # blank text
        {"person_name": "Valid", "testimonial_text": long_text},  # > 5000
        {"person_name": "x" * 201, "testimonial_text": "valid"},  # > 200 name
        {"person_name": "Valid", "testimonial_text": "valid", "rating": 0},
        {"person_name": "Valid", "testimonial_text": "valid", "rating": 6},
    ]
    for payload in cases:
        res = await client.post("/api/public/testimonials", json=payload)
        assert res.status_code == 422, (payload, res.status_code, res.text)

    stored = await get_mongo().database["testimonials"].find_one(
        {"person_name": {"$in": ["Valid", "   ", "x" * 201]}}
    )
    assert stored is None, "rejected submissions must never be persisted"


async def test_public_submit_trims_whitespace(client):
    res = await client.post(
        "/api/public/testimonials",
        json={"person_name": "  Ada  ", "testimonial_text": "  Great work.  "},
    )
    assert res.status_code == 201, res.text
    stored = await get_mongo().database["testimonials"].find_one(
        {"person_name": "Ada"}
    )
    assert stored["testimonial_text"] == "Great work."
    assert stored["status"] == "pending"
    assert stored["published"] is False


async def test_admin_delete_requires_csrf_header_then_auth(client, fetch_csrf):
    bad_id = "0123456789abcdef01234567"
    res = await client.delete(f"/api/testimonials/{bad_id}")
    assert res.status_code == 403
    assert res.json()["error"]["code"] == "CSRF_MISSING"

    csrf = await fetch_csrf()
    res = await client.delete(
        f"/api/testimonials/{bad_id}", headers={"X-CSRF-Token": csrf}
    )
    assert res.status_code == 401
    assert res.json()["error"]["code"] == "NOT_AUTHENTICATED"


async def test_login_rate_limit_ignores_forwarded_for_shared_bucket(
    client, make_admin, csrf_token
):
    settings = get_settings()
    await make_admin("proxied@example.com")

    for i in range(settings.LOGIN_RATE_LIMIT_MAX):
        res = await client.post(
            "/api/auth/login",
            json={"email": "proxied@example.com", "password": f"WrongPass-{i}"},
            headers={"X-CSRF-Token": csrf_token, "X-Forwarded-For": f"1.2.3.{i}"},
        )
        assert res.status_code == 401, res.text

    blocked = await client.post(
        "/api/auth/login",
        json={"email": "proxied@example.com", "password": "WrongPass-9"},
        headers={"X-CSRF-Token": csrf_token, "X-Forwarded-For": "9.9.9.9"},
    )
    assert blocked.status_code == 429
    assert blocked.json()["error"]["code"] == "RATE_LIMITED"
    assert int(blocked.headers["Retry-After"]) >= 1