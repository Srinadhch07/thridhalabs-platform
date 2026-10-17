"""Unit tests for the shared Mongo serialization boundary (`app.core.bson`).

The boundary must convert exactly the types BSON cannot encode
(`datetime.date`) while leaving every already-compatible value — datetimes,
ObjectIds, enums, primitives — byte-for-byte untouched.
"""

from __future__ import annotations

from datetime import date, datetime, timezone
from enum import Enum

from bson import ObjectId
from pydantic import BaseModel

from app.core.bson import serialize_for_mongo


class _Color(str, Enum):
    RED = "red"


class _Payload(BaseModel):
    when: date | None = None
    tags: list[str] = []


def test_date_becomes_iso_string_and_datetime_passes_through():
    aware = datetime(2026, 5, 22, 12, 30, tzinfo=timezone.utc)
    naive = datetime(2026, 5, 22, 12, 30)
    out = serialize_for_mongo({
        "completion_date": date(2026, 5, 22),
        "created_at": aware,
        "naive_at": naive,
    })
    assert out["completion_date"] == "2026-05-22"
    assert out["created_at"] is aware
    assert out["naive_at"] is naive


def test_nested_dicts_lists_and_tuples_are_recursed():
    out = serialize_for_mongo({
        "metadata": {"happened_on": date(2025, 11, 21)},
        "dates": [date(2025, 1, 1), None, "kept"],
        "pair": (date(2025, 2, 2), 7),
    })
    assert out["metadata"] == {"happened_on": "2025-11-21"}
    assert out["dates"] == ["2025-01-01", None, "kept"]
    assert out["pair"] == ("2025-02-02", 7)


def test_compatible_types_pass_through_untouched():
    oid = ObjectId()
    out = serialize_for_mongo({
        "ref": oid,
        "status": _Color.RED,
        "name": "x",
        "n": 3,
        "flag": True,
        "nothing": None,
    })
    assert out["ref"] is oid
    assert out["status"] is _Color.RED
    assert out == {
        "ref": oid, "status": _Color.RED, "name": "x",
        "n": 3, "flag": True, "nothing": None,
    }


def test_pydantic_models_are_dumped_then_encoded():
    out = serialize_for_mongo({"payload": _Payload(when=date(2026, 5, 22), tags=["a"])})
    assert out["payload"] == {"when": "2026-05-22", "tags": ["a"]}


def test_input_is_not_mutated():
    nested = {"when": date(2026, 5, 22)}
    data = {"nested": nested, "dates": [date(2026, 5, 22)]}
    serialize_for_mongo(data)
    assert nested == {"when": date(2026, 5, 22)}
    assert data["dates"] == [date(2026, 5, 22)]
