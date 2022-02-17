from __future__ import annotations

import re
from typing import Annotated, Any, Iterable, Literal

import frappe
from comfort import _, get_all
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
from frappe.model.meta import Meta
from frappe.utils import fmt_money, unique


def _format_weight(weight: int | float):
    return f"{float(weight)} кг"


def _parse_phone_number(phone: str):
    regex = re.compile(r"^((8|\+7)[\-– ]?)?(\(?\d{3}\)?[\-– ]?)?[\d\-– ]{7,10}$")
    if not re.match(regex, phone):
        return
    clean = re.sub(r"[^0-9]+", "", phone)
    if clean[:1] == "7":
        clean = "8" + clean[1:]
    return clean


def format_phone(phone: str):  # pragma: no cover
    parsed = _parse_phone_number(phone)
    if parsed is None:
        return phone
    if len(parsed) != 11:
        return parsed
    return f"{parsed[0]} ({parsed[1:4]}) {parsed[4:7]}–{parsed[7:9]}–{parsed[9:11]}"


def _format_item_query(  # pragma: no cover
    result: Annotated[list[Any], ["name", "item_name", "rate"]]
):
    result[2] = fmt_money(result[2])


def _format_purchase_order_query(  # pragma: no cover
    result: Annotated[list[Any], ["name", "status", "total_amount", "total_weight"]]
):
    result[2] = fmt_money(result[2])
    result[3] = _format_weight(result[3])


def _format_sales_order_query(  # pragma: no cover
    result: Annotated[list[Any], ["name", "status", "customer", "total_amount"]]
):
    result[3] = fmt_money(result[3])


def _format_customer_query(  # pragma: no cover
    result: Annotated[list[Any], ["name", "phone"]]
):
    result[1] = format_phone(str(result[1]))


_QUERY_FORMATTERS = {
    "Item": _format_item_query,
    "Purchase Order": _format_purchase_order_query,
    "Sales Order": _format_sales_order_query,
    "Customer": _format_customer_query,
}


def _get_fields(doctype: str, fields: list[str]) -> list[str]:  # pragma: no cover
    meta: Meta = frappe.get_meta(doctype)
    search_fields: list[str] = meta.get_search_fields()  # type: ignore
    fields.extend(search_fields)  # type: ignore

    title_field: str | None = meta.get("title_field")  # type: ignore
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
    order_by: str = "modified DESC",
):
    fields = _get_fields(doctype, [searchfield, "name"])

    resp: tuple[tuple[Any, ...], ...] = frappe.get_all(  # type: ignore
        doctype=doctype,
        fields=fields,
        filters=filters,
        or_filters=[(field, "like", "%%%s%%" % txt) for field in fields],
        order_by=order_by,
        limit_start=start,
        limit_page_length=page_len,
        as_list=True,
    )

    results: list[list[Any]] = [list(result) for result in resp]
    new_results: list[list[str]] = []

    for result in results:
        result: list[str] = [_(v) or "" for v in result]
        if doctype in _QUERY_FORMATTERS:
            _QUERY_FORMATTERS[doctype](result)
        new_results.append(result)

    return new_results


def get_standard_queries(doctypes: Iterable[str]):
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
    ignore_orders: list[str] | str = (
        get_all(
            PurchaseOrderSalesOrder,
            pluck="sales_order_name",
            field="sales_order_name",
            filter={"parent": ("!=", filters["docname"]), "docstatus": ("!=", 2)},
        )
        + filters["not in"]
    )

    ignore_orders_cond = ""
    if len(ignore_orders) > 0:
        ignore_orders = "(" + ",".join(f"'{d}'" for d in ignore_orders) + ")"
        ignore_orders_cond = f"name NOT IN {ignore_orders} AND"

    searchfields: list[Any] | str = frappe.get_meta("Sales Order").get_search_fields()
    if searchfield:
        searchfields = " or ".join(field + " LIKE %(txt)s" for field in searchfields)

    orders: list[list[Any]] = frappe.db.sql(  # type: ignore  # nosec
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
        order[2] = frappe.format(order[2], "Currency")
    return orders


@frappe.whitelist()
def sales_order_item_query(
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
            field="item_code",
            filter={"parent": ("in", from_purchase_order)},
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
