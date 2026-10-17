"""BSON-safe serialization boundary for MongoDB writes.

Pydantic/API models may use `datetime.date` for date-only fields, but PyMongo
cannot BSON-encode `date`. Services must pass dumped payloads through
`serialize_for_mongo` before handing documents to repositories, so there is
exactly one place where application types become storage types.

Rules (deliberately narrow — everything else passes through untouched):
- `datetime.datetime` is preserved as-is. BSON natively supports datetimes,
  so existing timestamp behavior (`created_at`, `updated_at`, …) never changes.
- `datetime.date` (excluding `datetime`, which subclasses it) becomes its ISO
  `YYYY-MM-DD` string. This matches the date-only API contract (string in,
  string out): reads coerce back through the Pydantic models, and ISO strings
  sort in calendar order.
- Plain dicts, lists and tuples are processed recursively; Pydantic models are
  dumped first (python mode) and then recursed into.
- Everything else — `ObjectId`, enums, strings, numbers, bools, `None` —
  passes through untouched, so existing Mongo types keep working.
"""

from __future__ import annotations

from datetime import date, datetime
from typing import Any

from pydantic import BaseModel


def _encode(value: Any) -> Any:
    # NOTE: `datetime` must be checked before `date` (subclass relationship).
    if isinstance(value, datetime):
        return value
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, BaseModel):
        return _encode(value.model_dump())
    if isinstance(value, dict):
        return {key: _encode(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_encode(item) for item in value]
    if isinstance(value, tuple):
        return tuple(_encode(item) for item in value)
    return value


def serialize_for_mongo(data: dict[str, Any]) -> dict[str, Any]:
    """Return a BSON-encodable copy of a Mongo-bound document fragment."""
    return {key: _encode(item) for key, item in data.items()}
