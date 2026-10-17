"""Shared pagination + sort helpers for content APIs."""

from __future__ import annotations

import math

from app.core.errors import AppError

MAX_PAGE_SIZE = 100


def page_count(total: int, page_size: int) -> int:
    return math.ceil(total / page_size) if total else 0


def resolve_sort(
    *,
    field: str,
    order: str,
    allowed: set[str],
    default: str,
) -> tuple[str, int]:
    """Map a caller-supplied (sort, order) pair to a whitelisted sort.

    Returns ``(field_name, pymongo_direction)``. Only whitelisted field names
    and literal asc/desc orders are accepted — arbitrary user input is never
    interpolated into a MongoDB sort expression.
    """
    import pymongo

    if field not in allowed:
        raise AppError(
            422,
            "INVALID_SORT",
            f"Sort field must be one of: {', '.join(sorted(allowed))}",
        )
    if order not in ("asc", "desc"):
        raise AppError(422, "INVALID_ORDER", "Order must be 'asc' or 'desc'")
    direction = pymongo.ASCENDING if order == "asc" else pymongo.DESCENDING
    return (field or default, direction)