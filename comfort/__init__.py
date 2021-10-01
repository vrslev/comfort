from __future__ import annotations

import json
import re
from collections import Counter, defaultdict
from typing import Any, Iterable, TypeVar

import frappe
from frappe.model.document import Document

_T = TypeVar("_T")

from frappe import _ as _gettext


def _(msg: Any, lang: str | None = None, context: str | None = None) -> str:
    return _gettext(msg, lang, context)


def count_qty(
    data: Iterable[Any], key_attr: str = "item_code", value_attr: str = "qty"
):
    """Count something (most often item quantity) in list of objects."""
    counter: Counter[str] = Counter()
    for item in data:
        counter[getattr(item, key_attr)] += getattr(item, value_attr) or 0
    return counter


def counters_are_same(first: Counter[str], second: Counter[str]):
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


class TypedDocument(Document):
    name: str | None
    doctype: str

    def get(
        self,
        key: dict[Any, Any] | str | None = None,
        filters: dict[Any, Any] | str | None = None,
        limit: int | None = None,
        default: dict[Any, Any] | str | None = None,
    ) -> str | Document | dict[str, Any] | None:
        return super().get(key=key, filters=filters, limit=limit, default=default)

    def get_password(
        self, fieldname: str = "password", raise_exception: bool = True
    ) -> str | None:
        return super().get_password(
            fieldname=fieldname, raise_exception=raise_exception
        )


# _T_c = TypeVar("_T_c", bound=Document)


# def get_doc(cls: type[_T_c], *args: Any, **kwargs: Any) -> _T_c:
#     doctype = " ".join(re.findall("[A-Z][a-z]*", cls.__name__))
#     return frappe.get_doc(doctype, *args, **kwargs)
