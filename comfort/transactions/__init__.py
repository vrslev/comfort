from __future__ import annotations

from collections import Counter
from copy import copy
from typing import Union

import frappe
from comfort import ValidationError, count_quantity, group_by_attr
from comfort.entities.doctype.child_item.child_item import ChildItem
from comfort.entities.doctype.item.item import Item
from comfort.transactions.doctype.purchase_order_item_to_sell.purchase_order_item_to_sell import (
    PurchaseOrderItemToSell,
)
from frappe import _
from frappe.model.document import Document

from .doctype.purchase_order.purchase_order import PurchaseOrder
from .doctype.purchase_return_item.purchase_return_item import PurchaseReturnItem
from .doctype.sales_order.sales_order import SalesOrder
from .doctype.sales_order_child_item.sales_order_child_item import SalesOrderChildItem
from .doctype.sales_order_item.sales_order_item import SalesOrderItem
from .doctype.sales_return_item.sales_return_item import SalesReturnItem

_AnyItems = list[
    Union[SalesOrderItem, SalesOrderChildItem, ChildItem, PurchaseOrderItemToSell]
]


class Return(Document):
    returned_paid_amount: int
    items: list[SalesReturnItem] | list[PurchaseReturnItem]

    @property
    def _voucher(self) -> SalesOrder | PurchaseOrder:
        pass

    def delete_empty_items(self):
        if not hasattr(self, "items") or self.items is None:
            self.items = []
        items = copy(self.items)
        self.items = []
        for item in items:
            if item.qty != 0:
                self.items.append(item)

    def _calculate_item_values(self):
        for item in self.items:
            item.amount = item.qty * item.rate

    def _calculate_returned_paid_amount(self):
        pass

    @frappe.whitelist()
    def calculate(self):  # pragma: no cover
        self._calculate_item_values()
        self._calculate_returned_paid_amount()

    def _get_remaining_qtys(self, items: _AnyItems):
        in_voucher = count_quantity(items)
        in_return = count_quantity(self.items)
        for item in in_voucher:
            in_voucher[item] -= in_return.get(item, 0)
        return (item for item in in_voucher.items() if item[1] > 0)

    def get_items_available_to_add(self) -> dict[str, str | int]:
        pass

    def _validate_new_item(self, counter: Counter[str], item: dict[str, str | int]):
        if not (
            item["item_code"] in counter
            and item["qty"] > 0
            and item["qty"] <= counter[item["item_code"]]
        ):
            raise ValidationError(
                _(
                    "Insufficient quantity {} for Item {}: expected not more than {}."
                ).format(item["qty"], item["item_code"], counter[item["item_code"]])
            )

    @frappe.whitelist()
    def add_items(self, items: list[dict[str, str | int]]):
        all_items = self.get_items_available_to_add()
        counter = count_quantity(frappe._dict(item) for item in all_items)

        for item in items:
            self._validate_new_item(counter, item)
            self.append(
                "items",
                {
                    "item_code": item["item_code"],
                    "item_name": item["item_name"],
                    "qty": item["qty"],
                    "rate": item["rate"],
                },
            )
            self.calculate()

    def _add_missing_fields_to_items(self, items: _AnyItems):
        items_with_rates: list[Item] = frappe.get_all(
            "Item",
            fields=("item_code", "item_name", "rate"),
            filters={
                "item_code": (
                    "in",
                    (i.item_code for i in items if not i.get("rate")),
                )
            },
        )
        grouped_items = group_by_attr(items_with_rates)

        for item in items:
            if not item.get("rate"):
                item.item_name = grouped_items[item.item_code][0].item_name
                item.rate = grouped_items[item.item_code][0].rate
