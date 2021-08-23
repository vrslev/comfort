from __future__ import annotations

import json
from collections import Counter, defaultdict
from typing import Any, Iterable, Literal, TypeVar

import frappe

__version__ = "0.2.0"

# TODO: Add tests to all utils
OrderTypes = Literal["Sales Order", "Purchase Order"]

T = TypeVar("T")


def count_quantity(
    data: Iterable[Any], key_key: str = "item_code", value_key: str = "qty"
):
    """Count something (most often quantity) in list of objects."""
    c: Counter[str] = Counter()
    for item in data:
        c[getattr(item, key_key)] += getattr(item, value_key)
    return c


def counters_are_same(first: Counter[str], second: Counter[str]):
    return len(set(first.items()).symmetric_difference(set(second.items()))) == 0


def group_by_key(data: Iterable[T], key: str = "item_code") -> dict[Any, list[T]]:
    """Group iterable of objects by key."""
    d: defaultdict[Any, list[T]] = defaultdict(list)
    for item in data:
        d[getattr(item, key)].append(item)
    return dict(d)


def maybe_json(value: T) -> T:
    """Normalize payload from frontend without messing type hints."""
    try:
        return json.loads(value)  # type: ignore
    except (json.JSONDecodeError, TypeError):
        return value


class ValidationError(Exception):
    """Linter-friendly wrapper around `frappe.throw`."""

    def __init__(
        self,
        msg: Any = "",
        exc: type[Exception] = frappe.exceptions.ValidationError,
        title: str | None = None,
        is_minimizable: bool | None = None,
        wide: str | None = None,
        as_list: bool = False,
    ):
        frappe.throw(
            msg,
            exc=exc,
            title=title,
            is_minimizable=is_minimizable,
            wide=wide,
            as_list=as_list,
        )
