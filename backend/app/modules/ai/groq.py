"""Server-side Groq provider client.

Calls the official Groq REST API (OpenAI-compatible Chat Completions) directly
with `httpx`. The provider is only ever reached from the backend — the API key
is never exposed to a browser, bundled into the frontend, stored in browser
storage or placed in a URL.

Safety properties:

- **Bounded timeouts** on connect/read/write/pool so a hung provider can never
  pin a worker indefinitely.
- **Bounded retries** with exponential backoff + jitter, and only for genuinely
  transient conditions (connect/read timeouts, transport errors, HTTP 429 and
  5xx). A 401/403/404/400 is never retried.
- **Redaction**: provider response bodies are only surfaced after the API key is
  scrubbed and the text is truncated. Error messages never contain credentials.
- **No report content is logged here** — this module never logs payloads.
"""

from __future__ import annotations

import asyncio
import random
import time

import httpx

from app.core.config import get_settings

_CONNECT_TIMEOUT = 5.0
_READ_TIMEOUT = 30.0
_WRITE_TIMEOUT = 10.0
_POOL_TIMEOUT = 5.0
_MAX_ATTEMPTS = 3
_BACKOFF_BASE = 0.5
_BACKOFF_CAP = 4.0
_MAX_ERROR_CHARS = 300
_RETRYABLE_STATUS = {429, 500, 502, 503, 504}


class GroqError(Exception):
    """A controlled, client-safe provider failure.

    `code` is a stable machine code (e.g. `GROQ_RATE_LIMITED`), `message` is a
    short human-readable string that never contains a credential or raw payload.
    """

    def __init__(
        self,
        code: str,
        message: str,
        *,
        retryable: bool = False,
        status: int | None = None,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.retryable = retryable
        self.status = status


def _base_url() -> str:
    return get_settings().GROQ_API_BASE_URL.rstrip("/")


def _timeout() -> httpx.Timeout:
    return httpx.Timeout(
        connect=_CONNECT_TIMEOUT,
        read=_READ_TIMEOUT,
        write=_WRITE_TIMEOUT,
        pool=_POOL_TIMEOUT,
    )


def _redact(text: str | None, secret: str | None) -> str | None:
    if text is None:
        return None
    value = text.strip()
    if secret:
        value = value.replace(secret, "[redacted]")
    value = " ".join(value.split())
    return value[:_MAX_ERROR_CHARS] or None


def _provider_message(response: httpx.Response) -> str | None:
    """Best-effort extraction of a provider error message from the JSON body."""
    try:
        body = response.json()
    except Exception:  # noqa: BLE001 - any parse failure is non-fatal
        return None
    if isinstance(body, dict):
        error = body.get("error")
        if isinstance(error, dict) and isinstance(error.get("message"), str):
            return error["message"]
        if isinstance(body.get("message"), str):
            return body["message"]
    return None


def _status_error(
    status: int, provider_message: str | None, secret: str | None
) -> GroqError:
    detail = _redact(provider_message, secret)
    if status in (401, 403):
        return GroqError(
            "GROQ_INVALID_KEY",
            "Groq rejected the API key. Check the key and try again.",
            status=status,
        )
    if status == 404:
        return GroqError(
            "GROQ_UNKNOWN_MODEL",
            detail or "The selected model was not found on Groq.",
            status=status,
        )
    if status == 429:
        return GroqError(
            "GROQ_RATE_LIMITED",
            "Groq rate limit reached. Wait a moment and try again.",
            retryable=True,
            status=status,
        )
    if status == 400:
        return GroqError(
            "GROQ_BAD_REQUEST",
            detail or "Groq rejected the request.",
            status=status,
        )
    if status >= 500:
        return GroqError(
            "GROQ_UNAVAILABLE",
            "Groq is temporarily unavailable. Try again shortly.",
            retryable=True,
            status=status,
        )
    return GroqError(
        "GROQ_ERROR",
        detail or "Groq request failed.",
        status=status,
    )


async def _request_json(
    method: str,
    path: str,
    *,
    api_key: str,
    json_body: dict | None = None,
) -> dict:
    """Perform a bounded, retrying JSON request to Groq."""
    url = f"{_base_url()}{path}"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Accept": "application/json",
    }
    if json_body is not None:
        headers["Content-Type"] = "application/json"

    last_exc: GroqError | None = None
    async with httpx.AsyncClient(timeout=_timeout()) as client:
        for attempt in range(1, _MAX_ATTEMPTS + 1):
            try:
                response = await client.request(
                    method, url, headers=headers, json=json_body
                )
            except (httpx.TimeoutException, httpx.TransportError) as exc:
                last_exc = GroqError(
                    "GROQ_UNREACHABLE",
                    "Could not reach Groq (network or timeout).",
                    retryable=True,
                )
                if attempt < _MAX_ATTEMPTS:
                    await asyncio.sleep(_backoff(attempt))
                    continue
                raise last_exc from exc

            if response.status_code >= 400:
                error = _status_error(
                    response.status_code,
                    _provider_message(response),
                    api_key,
                )
                if error.retryable and attempt < _MAX_ATTEMPTS:
                    last_exc = error
                    await asyncio.sleep(_backoff(attempt))
                    continue
                raise error

            try:
                return response.json()
            except Exception as exc:  # noqa: BLE001
                raise GroqError(
                    "GROQ_MALFORMED_RESPONSE",
                    "Groq returned an unreadable response.",
                ) from exc

    # Unreachable, but keeps the type checker satisfied.
    raise last_exc or GroqError("GROQ_ERROR", "Groq request failed.")


def _backoff(attempt: int) -> float:
    delay = min(_BACKOFF_BASE * (2 ** (attempt - 1)), _BACKOFF_CAP)
    return delay + random.uniform(0, delay / 2)


async def list_models(api_key: str) -> list[str]:
    """Fetch the available model ids (used to validate a key + model)."""
    data = await _request_json("GET", "/models", api_key=api_key)
    items = data.get("data") if isinstance(data, dict) else None
    if not isinstance(items, list):
        raise GroqError(
            "GROQ_MALFORMED_RESPONSE", "Groq returned an unreadable model list."
        )
    ids: list[str] = []
    for item in items:
        if isinstance(item, dict) and isinstance(item.get("id"), str):
            ids.append(item["id"])
    return ids


async def chat_completion(
    api_key: str,
    *,
    model: str,
    system_prompt: str,
    user_prompt: str,
    max_completion_tokens: int = 1024,
    temperature: float = 0.2,
) -> str:
    """Run a single chat completion and return the assistant text.

    Raises `GroqError` for every failure mode. `max_completion_tokens` bounds the
    provider-side cost; the prompts are constructed by the caller.
    """
    body = {
        "model": model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        "temperature": temperature,
        "max_completion_tokens": max_completion_tokens,
    }
    data = await _request_json(
        "POST", "/chat/completions", api_key=api_key, json_body=body
    )
    choices = data.get("choices") if isinstance(data, dict) else None
    if not isinstance(choices, list) or not choices:
        raise GroqError("GROQ_EMPTY_RESPONSE", "Groq returned no summary.")
    message = choices[0].get("message") if isinstance(choices[0], dict) else None
    content = message.get("content") if isinstance(message, dict) else None
    if not isinstance(content, str) or not content.strip():
        raise GroqError("GROQ_EMPTY_RESPONSE", "Groq returned an empty summary.")
    return content.strip()


async def test_connection(api_key: str, model: str | None) -> dict:
    """Validate a key (and, when given, a model) with a single cheap call.

    Returns a JSON-safe dict; raises `GroqError` on failure. The key is never
    included in the result.
    """
    started = time.perf_counter()
    models = await list_models(api_key)
    latency_ms = int((time.perf_counter() - started) * 1000)
    model_available = None if not model else (model in models)
    return {
        "models_available": len(models),
        "model_available": model_available,
        "latency_ms": latency_ms,
    }


__all__ = ["GroqError", "chat_completion", "list_models", "test_connection"]
