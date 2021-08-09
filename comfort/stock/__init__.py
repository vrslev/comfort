"""
STOCK CYCLE

  Purchased       SUPPLIER            -> available_purchased
                                      -> reserved_purchased
  Received        reserved_purchased  -> reserved_actual
                  available_purchased -> available_actual

* Client ordered  available_actual    -> reserved_actual
  something from
  Actual Stock

  Delivered       reserved_actual     -> CUSTOMER

? Client ordered something while items not received yet
    Instead of Select field `source`, the best way to implement injecting Sales Orders
    into Purchase Order would be button inside this Purchase Order with prompt to
    choose items and create Sales Order.
    This way no double links would be created, and it is much clearer.

    When Purchase Order completed,
    it's time to forget about it. But when it is pending, the hard way should be
    chosen: move items to sell to new Sales Order

    The only problem is that system can't force user to submit new Sales Order.

    So, there should be `from_actual_stock` check.

    1. If new Sales Order (will purchase specially for customer): nothing new
    2. If from Items To Sell:
        - if not received yet: add this Sales Order from Purchase Order
            (using button in Items To Sell grid)
        - else, if Purchase Order received, just create Sales Order normal way.

    To make this work:
    - [ ] Change `source` Select field to `from_actual_stock` check
    - [ ] Change functions related to this fields
    - [ ] Add mechanism to create Sales Order from Purchase Order that is
            not received yet



? Cancelled
"""

# TODO: What if someone bought something while items not received yet?
# TODO: Sales Order added this way should appear in Purchase order

from __future__ import annotations

from typing import Any, ItemsView

import frappe
from frappe import ValidationError, _
from frappe.model.document import Document
from frappe.utils.data import cint

from .doctype.bin.bin import fields

__all__ = [
    "update_bin",
    "purchase_order_purchased",
    "purchase_order_completed",
    "sales_order_from_stock_submitted",
    "sales_order_delivered",
]


def update_bin(item_code: str, **kwargs: int):
    doc = frappe.get_doc("Bin", item_code)

    for d in kwargs:
        if d not in fields:
            raise ValidationError(_(f"No such argument in Bin: {d}"))  # type: ignore

    for attr, qty in kwargs.items():
        new_qty = cint(getattr(doc, attr)) + cint(qty)  # type: ignore
        setattr(doc, attr, new_qty)

    doc.save()


def get_items_to_sell_for_bin(doc: Any) -> ItemsView[str, int]:
    if not doc.sales_orders:
        return []
    items_map: dict[str, Any] = {}
    for d in doc.items_to_sell:
        if d.item_code not in items_map:
            items_map[d.item_code] = 0
        items_map[d.item_code] += d.qty
    return items_map.items()


def get_sales_order_items_for_bin(doc: Document) -> ItemsView[str, int]:
    # TODO: use templated items instead (one that generates for cart)
    if not doc.sales_orders:
        return []
    sales_order_names = [d.sales_order_name for d in doc.sales_orders]
    so_items = frappe.db.sql(
        """
        SELECT item_code, qty
        FROM `tabSales Order Item`
        WHERE parent IN %(sales_orders)s
        AND qty > 0
    """,
        {"sales_orders": sales_order_names},
        as_dict=True,
    )

    packed_items = frappe.db.sql(
        """
        SELECT parent_item_code, item_code, qty
        FROM `tabSales Order Child Item`
        WHERE parent IN %(sales_orders)s
        AND qty > 0
    """,
        {"sales_orders": sales_order_names},
        as_dict=True,
    )

    parent_items = [d.parent_item_code for d in packed_items]
    so_items = [d for d in so_items if d.item_code not in parent_items]

    items = packed_items + so_items

    items_map: Any = {}
    for d in items:
        if d.item_code not in items_map:
            items_map[d.item_code] = 0
        items_map[d.item_code] += d.qty

    return items_map.items()


def purchase_order_purchased(doc: Document):
    for item_code, qty in get_sales_order_items_for_bin(doc):
        update_bin(item_code, reserved_purchased=qty)

    for item_code, qty in get_items_to_sell_for_bin(doc):
        update_bin(item_code, available_purchased=qty)


def purchase_order_completed(doc: Document):
    for item_code, qty in get_sales_order_items_for_bin(doc):
        update_bin(item_code, reserved_purchased=-qty, reserved_actual=qty)

    for item_code, qty in get_items_to_sell_for_bin(doc):
        update_bin(item_code, available_purchased=-qty, available_actual=qty)


def validate_items_available_for_sales_order_from_stock(
    doc: Document, item_to_qty: list[tuple[str]]
):
    field = "available_actual"
    item_availability: Any = frappe.get_all(
        "Bin",
        ["item_code", field],
        {"item_code": ["in", [d.item_code for d in doc.items]]},
    )
    item_availability_map: Any = {}
    for d in item_availability:
        if d.item_code not in item_availability_map:
            item_availability_map[d.item_code] = 0
        item_availability_map[d.item_code] += d[field]

    not_available_items: list[tuple[str | int]] = []
    for item_code, reqd_qty in item_to_qty:
        available_qty = item_availability_map[item_code]
        lack_qty = reqd_qty - available_qty
        if lack_qty > 0:
            not_available_items.append((item_code, lack_qty))

    if len(not_available_items) > 0:
        raise frappe.throw(
            _("Lack of quantity for items: {}").format(
                ", ".join(
                    [
                        f'<a href="/app/item/{d[0]}" data-doctype="Item"'
                        f' data-name="${d[0]}">{d[0]}</a> ({d[1]} шт)'
                        for d in not_available_items
                    ]
                )
            )
        )


def sales_order_from_stock_submitted(doc: Document):
    if doc.from_actual_stock:
        item_to_qty: tuple[str, int] = doc.get_item_qty_map(True).items()
        validate_items_available_for_sales_order_from_stock(doc, item_to_qty)
        for item_code, qty in item_to_qty:
            update_bin(item_code, available_actual=-qty, reserved_actual=qty)  # type: ignore


def sales_order_delivered(doc: Document):
    for item_code, qty in doc.get_item_qty_map(True).items():
        update_bin(item_code, reserved_actual=-qty)  # type: ignore
