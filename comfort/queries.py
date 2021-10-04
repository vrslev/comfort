from __future__ import annotations

from typing import Any, Iterable, Literal

import frappe
from comfort import get_all
from comfort.stock import get_stock_balance
from comfort.transactions.doctype.purchase_order_item_to_sell.purchase_order_item_to_sell import (
    PurchaseOrderItemToSell,
)
from comfort.transactions.doctype.purchase_order_sales_order.purchase_order_sales_order import (
    PurchaseOrderSalesOrder,
)
from comfort.transactions.doctype.sales_order.sales_order import (
    validate_params_from_available_stock,
)
from frappe.desk.reportview import get_filters_cond, get_match_cond
from frappe.model.meta import Meta
from frappe.utils import unique


def _format_money(money: str | int):  # pragma: no cover
    return f"{int(money)} ₽"


def _format_weight(weight: int | float):  # pragma: no cover
    return f"{float(weight)} кг"


def _format_item_query(d: list[Any]):  # pragma: no cover
    if d[2]:
        d[2] = _format_money(d[2])


def _format_purchase_order_query(d: list[Any]):  # pragma: no cover
    if d[2]:
        d[2] = _format_money(d[2])
    if d[3]:
        d[3] = _format_weight(d[3])


def _format_sales_order_query(d: list[Any]):  # pragma: no cover
    if d[3]:
        d[3] = _format_money(d[3])


_QUERY_FORMATTERS = {  # pragma: no cover
    "Item": _format_item_query,
    "Purchase Order": _format_purchase_order_query,
    "Sales Order": _format_sales_order_query,
}


def _get_fields(
    doctype: str, fields: list[Any] | None = None
) -> list[Any]:  # pragma: no cover
    # From ERPNext
    if fields is None:
        fields = []
    meta: Meta = frappe.get_meta(doctype)
    search_fields: list[Any] = meta.get_search_fields()
    fields.extend(search_fields)

    title_field: Any = meta.get("title_field")
    if title_field and not title_field.strip() in fields:
        fields.insert(1, title_field.strip())

    return unique(fields)


@frappe.whitelist()  # pragma: no cover
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

    query: list[list[Any]] = frappe.db.sql(  # type: ignore
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


def get_standard_queries(doctypes: Iterable[str]):  # pragma: no cover
    query_name = default_query.__module__ + "." + default_query.__name__
    return {d: query_name for d in doctypes}


@frappe.whitelist()
@frappe.validate_and_sanitize_search_inputs  # pragma: no cover
def purchase_order_sales_order_query(
    doctype: str,
    txt: str,
    searchfield: str,
    start: str,
    page_len: str,
    filters: dict[str, Any],
):
    ignore_orders: list[str] | str = [
        s.sales_order_name
        for s in get_all(
            PurchaseOrderSalesOrder,
            "sales_order_name",
            {"parent": ("!=", filters["docname"])},
        )
    ] + filters["not in"]

    ignore_orders_cond = ""
    if len(ignore_orders) > 0:
        ignore_orders = "(" + ",".join(f"'{d}'" for d in ignore_orders) + ")"
        ignore_orders_cond = f"name NOT IN {ignore_orders} AND"

    searchfields: list[Any] | str = frappe.get_meta("Sales Order").get_search_fields()
    if searchfield:
        searchfields = " or ".join(field + " LIKE %(txt)s" for field in searchfields)

    orders: list[list[str | int]] = frappe.db.sql(  # type: ignore  # nosec
        """
        SELECT name, customer, total_amount from `tabSales Order`
        WHERE {ignore_orders_cond}
        status NOT IN ('Closed', 'Completed', 'Cancelled')
        AND ({scond})
        ORDER BY modified DESC
        LIMIT %(start)s, %(page_len)s
        """.format(
            scond=searchfields, ignore_orders_cond=ignore_orders_cond
        ),
        {"txt": "%%%s%%" % txt, "start": start, "page_len": page_len},
        as_list=True,
    )

    for order in orders:
        order[2] = frappe.format(order[2], "Currency")  # type: ignore
    return orders


@frappe.whitelist()
def sales_order_item_query(  # TODO: Cover
    doctype: str,
    txt: str,
    searchfield: str,
    start: int,
    page_len: int,
    filters: dict[str, Any],
):  # pragma: no cover
    from_available_stock: Literal[
        "Available Purchased", "Available Actual"
    ] | None = filters.get("from_available_stock")
    from_purchase_order: str | None = filters.get("from_purchase_order")

    validate_params_from_available_stock(from_available_stock, from_purchase_order)

    acceptable_item_codes: Iterable[str] | None = None

    if from_available_stock == "Available Actual":
        acceptable_item_codes = get_stock_balance(from_available_stock).keys()
    elif from_available_stock == "Available Purchased":
        items_to_sell = get_all(
            PurchaseOrderItemToSell,
            fields="item_code",
            filters={"parent": ("in", from_purchase_order)},
        )
        acceptable_item_codes = (d.item_code for d in items_to_sell)

    if acceptable_item_codes is None:
        filters = {}
    else:
        filters = {"item_code": ("in", acceptable_item_codes)}

    return default_query(
        doctype=doctype,
        txt=txt,
        searchfield=searchfield,
        start=start,
        page_len=page_len,
        filters=filters,
    )