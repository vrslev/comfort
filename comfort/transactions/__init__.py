from __future__ import annotations

from collections import Counter
from copy import copy
from typing import Callable, Union

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

_AnyItem = Union[
    SalesOrderItem, SalesOrderChildItem, ChildItem, PurchaseOrderItemToSell
]


class Return(Document):
    returned_paid_amount: int
    items: list[SalesReturnItem] | list[PurchaseReturnItem]

    @property
    def _voucher(self) -> SalesOrder | PurchaseOrder:
        pass

    def _calculate_returned_paid_amount(self):
        pass

    def _validate_voucher_statuses(self):
        pass

    def _get_all_items(
        self,
    ) -> list[_AnyItem] | list[SalesOrderChildItem | SalesOrderItem]:
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

    @frappe.whitelist()
    def calculate(self):  # pragma: no cover
        self._calculate_item_values()
        self._calculate_returned_paid_amount()

    def _get_remaining_qtys(self, items: list[_AnyItem]):
        in_voucher = count_quantity(items)
        in_return = count_quantity(self.items)
        for item in in_voucher:
            in_voucher[item] -= in_return.get(item, 0)
        return (item for item in in_voucher.items() if item[1] > 0)

    def _add_missing_fields_to_items(self, items: list[_AnyItem]):
        items_with_rates: list[Item] = frappe.get_all(
            "Item",
            fields=("item_code", "item_name", "rate"),
            filters={
                "item_code": ("in", (i.item_code for i in items if not i.get("rate")))
            },
        )
        grouped_items = group_by_attr(items_with_rates)

        for item in items:
            if not item.get("rate"):
                item.item_name = grouped_items[item.item_code][0].item_name
                item.rate = grouped_items[item.item_code][0].rate

    @frappe.whitelist()
    def get_items_available_to_add(self):
        self.delete_empty_items()
        items = merge_items(self._get_all_items())
        self._add_missing_fields_to_items(items)
        available_item_and_qty = self._get_remaining_qtys(items)
        grouped_items = group_by_attr(items)

        res: dict[str, str | int] = [
            {
                "item_code": item_code,
                "item_name": grouped_items[item_code][0].item_name,
                "qty": qty,
                "rate": grouped_items[item_code][0].rate,
            }
            for item_code, qty in available_item_and_qty
        ]
        sort_by: Callable[[res], str] = lambda i: i["item_name"]
        res.sort(key=sort_by)
        return res

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

    def _validate_not_all_items_returned(self):
        if len([i for i in self._get_remaining_qtys(self._get_all_items())]) == 0:
            raise ValidationError(_("Can't return all items"))

    def validate(self):  # pragma: no cover
        self.delete_empty_items()
        self._validate_voucher_statuses()
        self._validate_not_all_items_returned()
        self.calculate()

    def before_cancel(self):
        raise ValidationError(_("Not allowed to cancel Return"))


def merge_items(items: list[_AnyItem]):  # TODO: Cover
    counter = count_quantity(items)
    merged_items: list[_AnyItem] = []

    for item_code, cur_items in group_by_attr(items).items():
        cur_items[0].qty = counter[item_code]
        merged_items.append(cur_items[0])
    return merged_items
