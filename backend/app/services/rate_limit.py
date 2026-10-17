"""In-memory login rate limiting.

Counts FAILED login attempts per client IP inside a fixed window driven by
`LOGIN_RATE_LIMIT_MAX` / `LOGIN_RATE_LIMIT_WINDOW_MINUTES`.

Limitations (documented by design):
- process-local: counters reset on restart and are NOT shared between
  multiple workers/instances;
- replaceable: the interface is tiny, so a distributed limiter (e.g. Redis)
  can be swapped in later without touching the login service.
"""

from __future__ import annotations

import math
import time


class LoginRateLimiter:
    def __init__(self) -> None:
        # key -> (failure_count, window_started_at)
        self._failures: dict[str, tuple[int, float]] = {}

    def is_limited(
        self,
        key: str,
        *,
        max_attempts: int,
        window_seconds: float,
        now: float | None = None,
    ) -> tuple[bool, int]:
        """Return (limited, retry_after_seconds)."""
        now = time.monotonic() if now is None else now
        entry = self._failures.get(key)
        if entry is None:
            return False, 0
        count, started = entry
        if now - started >= window_seconds:
            return False, 0
        if count >= max_attempts:
            retry_after = max(1, math.ceil(window_seconds - (now - started)))
            return True, retry_after
        return False, 0

    def record_failure(
        self,
        key: str,
        *,
        max_attempts: int,
        window_seconds: float,
        now: float | None = None,
    ) -> None:
        now = time.monotonic() if now is None else now
        count, started = self._failures.get(key, (0, now))
        if now - started >= window_seconds:
            count, started = 0, now
        self._failures[key] = (count + 1, started)
        if len(self._failures) > 10_000:  # opportunistic hygiene
            self._purge(window_seconds, now)

    def reset(self, key: str) -> None:
        self._failures.pop(key, None)

    def clear(self) -> None:
        self._failures.clear()

    def _purge(self, window_seconds: float, now: float) -> None:
        expired = [
            key
            for key, (_, started) in self._failures.items()
            if now - started >= window_seconds
        ]
        for key in expired:
            self._failures.pop(key, None)


login_rate_limiter = LoginRateLimiter()
# Separate bucket for member onboarding ("set password") attempts so a burst of
# bad setup links cannot lock out normal sign-ins, and vice versa.
onboarding_rate_limiter = LoginRateLimiter()
