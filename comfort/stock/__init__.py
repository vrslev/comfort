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

from typing import ItemsView

import frappe
from comfort import count_quantity
from comfort.stock.doctype.bin.bin import Bin
from frappe import _
from frappe.model.document import Document

# TODO: Don't really need to do this since decided to move to Mixin system for transactions
__all__ = [
    "purchase_order_purchased",
    "purchase_order_completed",
]


def get_items_to_sell_for_bin(
    doc: Document,
) -> ItemsView[str, int]:  # TODO: Test this
    if not doc.sales_orders:  # TODO: What?
        return []
    return count_quantity(doc.items_to_sell).items()  # type: ignore


def get_sales_order_items_for_bin(doc: Document) -> ItemsView[str, int]:
    # TODO: use templated items instead (one that generates for cart)
    if not doc.sales_orders:
        return []
    sales_order_names = [d.sales_order_name for d in doc.sales_orders]
    so_items: list[dict[str, str | int]] = frappe.db.sql(
        """
        SELECT item_code, qty
        FROM `tabSales Order Item`
        WHERE parent IN %(sales_orders)s
        AND qty > 0
    """,
        {"sales_orders": sales_order_names},
        as_dict=True,
    )

    packed_items: list[dict[str, str | int]] = frappe.db.sql(
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

    # TODO: Test this
    return count_quantity(items).items()


def purchase_order_purchased(doc: Document):
    for item_code, qty in get_sales_order_items_for_bin(doc):
        Bin.update_for(item_code, reserved_purchased=qty)

    for item_code, qty in get_items_to_sell_for_bin(doc):
        Bin.update_for(item_code, available_purchased=qty)


def purchase_order_completed(doc: Document):
    for item_code, qty in get_sales_order_items_for_bin(doc):

        Bin.update_for(item_code, reserved_purchased=-qty, reserved_actual=qty)

    for item_code, qty in get_items_to_sell_for_bin(doc):
        Bin.update_for(item_code, available_purchased=-qty, available_actual=qty)
