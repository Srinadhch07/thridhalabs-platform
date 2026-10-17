"""Login rate limiting: threshold behaviour and window semantics."""

from __future__ import annotations

from app.core.config import get_settings
from app.services.rate_limit import LoginRateLimiter, login_rate_limiter

PASSWORD = "CorrectHorse!Battery9"


async def _fail_login(client, csrf_token, email: str, password: str = "WrongPass!99"):
    return await client.post(
        "/api/auth/login",
        json={"email": email, "password": password},
        headers={"X-CSRF-Token": csrf_token},
    )


async def test_blocking_after_max_failures_even_with_correct_password(
    make_admin, client, csrf_token
):
    settings = get_settings()
    await make_admin("limited@example.com")

    for _ in range(settings.LOGIN_RATE_LIMIT_MAX):
        res = await _fail_login(client, csrf_token, "limited@example.com")
        assert res.status_code == 401

    blocked = await _fail_login(
        client, csrf_token, "limited@example.com", password=PASSWORD
    )
    assert blocked.status_code == 429
    error = blocked.json()["error"]
    assert error["code"] == "RATE_LIMITED"
    assert "Retry-After" in blocked.headers
    assert int(blocked.headers["Retry-After"]) >= 1


async def test_rate_limited_body_has_no_internal_details(
    make_admin, client, csrf_token
):
    settings = get_settings()
    await make_admin("shape@example.com")
    for _ in range(settings.LOGIN_RATE_LIMIT_MAX):
        await _fail_login(client, csrf_token, "shape@example.com")

    res = await _fail_login(client, csrf_token, "shape@example.com")
    assert res.status_code == 429
    body = res.json()
    assert set(body) == {"error"}
    assert set(body["error"]) == {"code", "message"}


async def test_successful_login_resets_failure_counter(
    make_admin, client, fetch_csrf
):
    settings = get_settings()
    await make_admin("reset@example.com")

    csrf_token = await fetch_csrf()
    for _ in range(settings.LOGIN_RATE_LIMIT_MAX - 1):
        res = await _fail_login(client, csrf_token, "reset@example.com")
        assert res.status_code == 401

    ok = await _fail_login(client, csrf_token, "reset@example.com", password=PASSWORD)
    assert ok.status_code == 200

    # A successful login rotates the CSRF cookie — fetch a fresh token.
    csrf_token = await fetch_csrf()
    # Counter was cleared by the success — one more failure is a plain 401.
    res = await _fail_login(client, csrf_token, "reset@example.com")
    assert res.status_code == 401


def test_limited_windows_expire_after_window_seconds():
    limiter = LoginRateLimiter()
    for _ in range(3):
        limiter.record_failure("ip", max_attempts=3, window_seconds=60, now=1000.0)

    limited, retry_after = limiter.is_limited(
        "ip", max_attempts=3, window_seconds=60, now=1030.0
    )
    assert limited is True
    assert retry_after == 30

    limited, _ = limiter.is_limited(
        "ip", max_attempts=3, window_seconds=60, now=1061.0
    )
    assert limited is False, "window must expire"


def test_reset_clears_the_counter():
    limiter = LoginRateLimiter()
    for _ in range(3):
        limiter.record_failure("ip", max_attempts=3, window_seconds=60, now=1000.0)
    assert limiter.is_limited("ip", max_attempts=3, window_seconds=60, now=1001.0)[0]

    limiter.reset("ip")
    assert limiter.is_limited("ip", max_attempts=3, window_seconds=60, now=1002.0)[0] is False


def test_counters_are_isolated_per_client_key():
    limiter = LoginRateLimiter()
    for _ in range(3):
        limiter.record_failure("a", max_attempts=3, window_seconds=60, now=1000.0)
    assert limiter.is_limited("a", max_attempts=3, window_seconds=60, now=1001.0)[0]
    assert limiter.is_limited("b", max_attempts=3, window_seconds=60, now=1001.0)[0] is False
