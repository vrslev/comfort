from __future__ import annotations

import json
from collections import Counter, defaultdict
from typing import Any, Iterable, Literal, TypeVar

import frappe

__version__ = "0.2.0"

OrderTypes = Literal["Sales Order", "Purchase Order"]  # pragma: no cover

_T = TypeVar("_T")


def count_quantity(
    data: Iterable[Any], key_attr: str = "item_code", value_attr: str = "qty"
):
    """Count something (most often item quantity) in list of objects."""
    counter: Counter[str] = Counter()
    for item in data:
        counter[getattr(item, key_attr)] += getattr(item, value_attr) or 0
    return counter


def are_same_counters(first: Counter[str], second: Counter[str]):
    return len(set(first.items()).symmetric_difference(set(second.items()))) == 0


def group_by_attr(data: Iterable[_T], attr: str = "item_code") -> dict[Any, list[_T]]:
    """Group iterable of objects by attribute."""
    ddict: defaultdict[Any, list[_T]] = defaultdict(list)
    for item in data:
        ddict[getattr(item, attr)].append(item)
    return dict(ddict)


def maybe_json(value: _T) -> _T:
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
