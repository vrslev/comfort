from __future__ import annotations

import json
from collections import Counter, defaultdict
from typing import Any, Iterable, TypeVar, cast, overload

import frappe
import frappe.auth
import frappe.utils
import frappe.utils.data
from comfort.integrations import sentry
from frappe import _ as _gettext
from frappe.model.document import Document


def _(msg: Any, lang: str | None = None, context: str | None = None) -> str:
    return _gettext(msg, lang, context)  # type: ignore


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


_T = TypeVar("_T")


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
    name: str
    doctype: str

    def get(
        self,
        key: dict[Any, Any] | str | None = None,
        filters: dict[Any, Any] | str | None = None,
        limit: int | None = None,
        default: dict[Any, Any] | str | None = None,
    ) -> Any:
        return super().get(key=key, filters=filters, limit=limit, default=default)  # type: ignore

    def insert(
        self,
        ignore_permissions: bool | None = None,
        ignore_links: bool | None = None,
        ignore_if_duplicate: bool = False,
        ignore_mandatory: bool | None = None,
        set_name: bool | None = None,
        set_child_names: bool = True,
    ):
        super().insert(
            ignore_permissions=ignore_permissions,
            ignore_links=ignore_links,
            ignore_if_duplicate=ignore_if_duplicate,
            ignore_mandatory=ignore_mandatory,
            set_name=set_name,
            set_child_names=set_child_names,
        )
        return self

    def save(  # type: ignore
        self, ignore_permissions: bool | None = None, ignore_version: bool | None = None
    ):
        super().save(
            ignore_permissions=ignore_permissions, ignore_version=ignore_version
        )

    def save_without_validating(self):
        self.flags.ignore_validate = True
        self.flags.ignore_validate_update_after_submit = True
        self.flags.ignore_links = True
        self.save()


_T_doc = TypeVar("_T_doc", bound=Document)


def _resolve_doctype_from_class(cls: type[Document]):
    doctype = cls.__name__
    if doctype == "DocType":
        return doctype  # pragma: no cover

    for i in range(len(doctype) - 1)[::-1]:
        if doctype[i].isupper() and doctype[i + 1].islower():
            doctype = doctype[:i] + " " + doctype[i:]
        if doctype[i].isupper() and doctype[i - 1].islower():
            doctype = doctype[:i] + " " + doctype[i:]
    doctype = doctype[1:]
    return doctype


def get_doc(cls: type[_T_doc], *args: Any, **kwargs: Any) -> _T_doc:
    doctype = _resolve_doctype_from_class(cls)
    if args and isinstance(args[0], dict):
        args[0]["doctype"] = doctype
        return frappe.get_doc(args[0])  # type: ignore
    if not args and not kwargs:
        args = (doctype,)
    return frappe.get_doc(doctype, *args, **kwargs)  # type: ignore


@overload
def get_all(
    cls: type[_T_doc],
    *,
    pluck: None,
    field: str | tuple[str, ...] | None = None,
    filter: dict[str, Any] | tuple[tuple[Any, ...], ...] | None = None,
    limit: int | None = None,
    order_by: str | None = None,
) -> list[_T_doc]:
    ...


@overload
def get_all(
    cls: type[_T_doc],
    *,
    pluck: None = None,
    field: str | tuple[str, ...] | None = None,
    filter: dict[str, Any] | tuple[tuple[Any, ...], ...] | None = None,
    limit: int | None = None,
    order_by: str | None = None,
) -> list[_T_doc]:
    ...


@overload
def get_all(
    cls: type[_T_doc],
    *,
    pluck: str,
    field: str | tuple[str, ...] | None = None,
    filter: dict[str, Any] | tuple[tuple[Any, ...], ...] | None = None,
    limit: int | None = None,
    order_by: str | None = None,
) -> list[Any]:
    ...


def get_all(
    cls: type[_T_doc],
    *,
    pluck: str | None = None,
    field: str | tuple[str, ...] | None = None,
    filter: dict[str, Any] | tuple[tuple[Any, ...], ...] | None = None,
    limit: int | None = None,
    order_by: str | None = None,
) -> list[_T_doc]:
    return cast(
        list[_T_doc],
        frappe.get_all(
            _resolve_doctype_from_class(cls),
            fields=field,
            filters=filter,
            pluck=pluck,
            limit_page_length=limit,
            order_by=order_by,
        ),
    )


def get_value(
    doctype: str,
    filters: str | dict[str, Any] | None = None,
    fieldname: str | Iterable[str] = "name",
    as_dict: bool = False,
    order_by: str | None = None,
) -> Any:
    return frappe.db.get_value(  # type: ignore
        doctype=doctype,
        filters=filters,
        fieldname=fieldname,
        as_dict=as_dict,
        order_by=order_by,
    )


def new_doc(cls: type[_T_doc]) -> _T_doc:
    return frappe.new_doc(_resolve_doctype_from_class(cls))  # type: ignore


def get_cached_doc(cls: type[_T_doc], name: str | None = None) -> _T_doc:
    doctype = _resolve_doctype_from_class(cls)
    if name is None:
        name = doctype
    return frappe.get_cached_doc(doctype, name)  # type: ignore


def get_cached_value(
    doctype: str, name: str, fieldname: str | Iterable[str], as_dict: bool = False
) -> Any:
    return frappe.get_cached_value(  # type: ignore
        doctype=doctype,
        name=name,
        fieldname=fieldname,
        as_dict=as_dict,
    )


def doc_exists(
    doctype: str | dict[str, Any], name: str | dict[str, Any] | None = None
) -> tuple[tuple[str]] | None:
    return frappe.db.exists(dt=doctype, dn=name)  # type: ignore


def copy_doc(doc: _T_doc, ignore_no_copy: bool = True) -> _T_doc:
    return frappe.copy_doc(doc, ignore_no_copy=ignore_no_copy)  # type: ignore


def patch_fmt_money():  # pragma: no cover
    old_func = frappe.utils.data.fmt_money  # type: ignore

    def fmt_money(
        amount: str | int | float,
        precision: int | None = None,
        currency: str | None = None,
        format: str | None = None,
    ) -> str:
        return old_func(amount, precision=0) + " ₽"  # type: ignore

    frappe.utils.data.fmt_money = fmt_money
    frappe.utils.fmt_money = fmt_money


def patch_validate_ip_address():
    def mock_validate_ip_address(user: Any):
        return

    frappe.auth.validate_ip_address = mock_validate_ip_address


sentry.init()
patch_fmt_money()
patch_validate_ip_address()
