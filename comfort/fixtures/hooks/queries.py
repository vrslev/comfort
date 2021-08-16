from __future__ import annotations

from typing import Any, Callable

import frappe
from frappe.desk.reportview import get_filters_cond, get_match_cond
from frappe.model.meta import Meta
from frappe.utils import unique


def _get_fields(doctype: str, fields: list[Any] | None = None) -> list[Any]:
    # From ERPNext
    if fields is None:
        fields = []
    meta: Meta = frappe.get_meta(doctype)
    search_fields: list[Any] = meta.get_search_fields()
    fields.extend(search_fields)

    title_field: str | None = meta.get("title_field")  # type: ignore
    if title_field and not title_field.strip() in fields:
        fields.insert(1, title_field.strip())

    return unique(fields)


def _format_money(money: str | int):
    return f"{int(money)} ₽"


def _format_weight(weight: int | float):
    return f"{float(weight)} кг"


def _format_item_query(d: list[Any]):
    if d[2]:
        d[2] = _format_money(d[2])


def _format_purchase_order_query(d: list[Any]):
    if d[2]:
        d[2] = _format_money(d[2])
    if d[3]:
        d[3] = _format_weight(d[3])


def format_sales_order_query(d: list[Any]):
    if d[3]:
        d[3] = _format_money(d[3])


_QUERY_FORMATTERS: dict[str, Callable[..., Any]] = {
    "Item": _format_item_query,
    "Purchase Order": _format_purchase_order_query,
    "Sales Order": format_sales_order_query,
}


@frappe.whitelist()
@frappe.validate_and_sanitize_search_inputs
def default_query(
    doctype: str,
    txt: str,
    searchfield: str,
    start: int,
    page_len: int,
    filters: dict[Any, Any],
):
    conditions = []
    fields = _get_fields(doctype, ["name"])

    query: list[tuple[Any]] = frappe.db.sql(
        f"""
        SELECT {", ".join(fields)} FROM `tab{doctype}`
        WHERE {searchfield} LIKE %(txt)s
        {get_filters_cond(doctype, filters, conditions)}
        {get_match_cond(doctype)}

        ORDER BY modified DESC
        LIMIT {start}, {page_len}
        """,
        {"txt": "%%%s%%" % txt},
        as_list=True,
    )
    if doctype in _QUERY_FORMATTERS:
        for d in query:
            _QUERY_FORMATTERS[doctype](d)
    return query


def get_standard_queries(doctypes: list[str]):
    query_name = default_query.__module__ + "." + default_query.__name__
    return {d: query_name for d in doctypes}
