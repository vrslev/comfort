"""
Delivery Statuses

# "To Purchase"
Stock Entry : None
GL Entry: None

# "Purchased"
Stock Entry: "Reserved Purchased" -> "Available Purchased"
GL Entry: None

# "To Deliver" or "Delivered"
Stock Entry: "Reserved Actual" -> "Available Actual"
GL Entry: "Cost of Goods Sold" -> "Inventory"



Payment Statuses
["Unpaid", "Partially Paid", "Paid", "Overpaid"]

# Unpaid
None

# Partially Paid

# Paid
GL Entry: "Cash" or "Bank" -> "Sales"

# Overpaid

"""
from __future__ import annotations

import frappe
from comfort import ValidationError, count_quantity, group_by_attr
from comfort.entities.doctype.item.item import Item
from frappe import _
from frappe.model.document import Document

from ..sales_order.sales_order import SalesOrder
from ..sales_order_child_item.sales_order_child_item import SalesOrderChildItem
from ..sales_order_item.sales_order_item import SalesOrderItem
from ..sales_return_item.sales_return_item import SalesReturnItem


# TODO: Observe case when all items are returned
class SalesReturn(Document):
    sales_order: str
    total_amount: int
    items: list[SalesReturnItem]

    def _get_items_in_sales_order(self):
        sales_order: SalesOrder = frappe.get_doc("Sales Order", self.sales_order)
        items = sales_order._get_items_with_splitted_combinations()
        _add_rates_to_child_items(items)
        return items

    def _get_remaining_qtys(
        self, items_in_sales_order: list[SalesOrderItem | SalesOrderChildItem]
    ):
        in_order = count_quantity(items_in_sales_order)
        in_return = count_quantity(self.items)
        for item in in_order:
            in_order[item] -= in_return.get(item, 0)
        return (item for item in in_order.items() if item[1] > 0)

    @frappe.whitelist()
    def get_items_available_to_add(self) -> dict[str, str | int]:
        items_in_order = self._get_items_in_sales_order()
        available_item_and_qty = self._get_remaining_qtys(items_in_order)
        grouped_items = group_by_attr(items_in_order)

        return [
            {
                "item_code": item_code,
                "item_name": grouped_items[item_code][0].item_name,
                "qty": qty,
                "rate": grouped_items[item_code][0].rate,
            }
            for item_code, qty in available_item_and_qty
        ]

    @frappe.whitelist()
    def calculate_amounts(self):
        self.total_amount = 0
        for item in self.items:
            item.amount = item.qty * item.rate
            self.total_amount += item.amount

    @frappe.whitelist()
    def add_items(self, items: list[dict[str, str | int]]):
        all_items = self.get_items_available_to_add()
        counter = count_quantity(frappe._dict(d) for d in all_items)

        for item in items:
            if (
                item["item_code"] in counter
                and item["qty"] > 0
                and item["qty"] <= counter[item["item_code"]]
            ):
                self.append(
                    "items",
                    {
                        "item_code": item["item_code"],
                        "item_name": item["item_name"],
                        "qty": item["qty"],
                        "rate": item["rate"],
                    },
                )
                self.calculate_amounts()
            else:
                raise ValidationError(
                    _(
                        "Insufficient quantity {} for Item {}: expected not more than {}."
                    ).format(
                        item["qty"],
                        item["item_code"],
                        counter[item["item_code"]],
                    )
                )


def _add_rates_to_child_items(items: list[SalesOrderItem | SalesOrderChildItem]):
    items_with_rates: list[Item] = frappe.get_all(
        "Item",
        fields=("item_code", "rate"),
        filters={
            "item_code": (
                "in",
                (i.item_code for i in items if i.doctype == "Sales Order Child Item"),
            )
        },
    )

    rates_map: dict[str, int] = {}
    for item in items_with_rates:
        if item.item_code not in rates_map:
            rates_map[item.item_code] = item.rate

    for item in items:
        if item.doctype == "Sales Order Child Item":
            item.rate = rates_map.get(item.item_code, 0)
