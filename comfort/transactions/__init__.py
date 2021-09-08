from __future__ import annotations

from collections import Counter
from copy import copy
from typing import Callable, Literal, TypeVar, Union

import frappe
from comfort import ValidationError, count_qty, group_by_attr
from comfort.entities.doctype.child_item.child_item import ChildItem
from comfort.entities.doctype.item.item import Item
from comfort.transactions.doctype.purchase_order_item_to_sell.purchase_order_item_to_sell import (
    PurchaseOrderItemToSell,
)
from frappe import _
from frappe.model.document import Document

from .doctype.purchase_return_item.purchase_return_item import PurchaseReturnItem
from .doctype.sales_order_child_item.sales_order_child_item import SalesOrderChildItem
from .doctype.sales_order_item.sales_order_item import SalesOrderItem
from .doctype.sales_return_item.sales_return_item import SalesReturnItem

AnyChildItem = Union[
    SalesOrderItem, SalesOrderChildItem, ChildItem, PurchaseOrderItemToSell
]
OrderTypes = Literal["Sales Order", "Purchase Order"]  # pragma: no cover


class Return(Document):
    returned_paid_amount: int
    items: list[SalesReturnItem] | list[PurchaseReturnItem]

    @property
    def _voucher(self) -> Document:
        pass

    def _calculate_returned_paid_amount(self):
        pass

    def _validate_voucher_statuses(self):
        pass

    def _get_all_items(
        self,
    ) -> list[AnyChildItem] | list[SalesOrderChildItem | SalesOrderItem]:
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

    def _get_remaining_qtys(self, items: list[AnyChildItem]):
        in_voucher = count_qty(items)
        in_return = count_qty(self.items)
        for item in in_voucher:
            in_voucher[item] -= in_return.get(item, 0)
        return (item for item in in_voucher.items() if item[1] > 0)

    def _add_missing_fields_to_items(self, items: list[AnyChildItem]):
        items_with_missing_fields: list[Item] = frappe.get_all(
            "Item",
            fields=("item_code", "item_name", "rate"),
            filters={
                "item_code": ("in", (i.item_code for i in items if not i.get("rate")))
            },
        )
        grouped_items = group_by_attr(items_with_missing_fields)

        for item in items:
            if not item.get("rate"):
                item.item_name = grouped_items[item.item_code][0].item_name
                item.rate = grouped_items[item.item_code][0].rate

    @frappe.whitelist()
    def get_items_available_to_add(self):
        self.delete_empty_items()
        items = merge_same_items(self._get_all_items())
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
        counter = count_qty(frappe._dict(item) for item in all_items)

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


_T = TypeVar("_T")


def delete_empty_items(self: object, items_field: str):
    """Delete items that have zero quantity."""
    items: list[AnyChildItem] = getattr(self, items_field)
    new_items: list[AnyChildItem] = []
    for item in items:
        if item.qty != 0:
            new_items.append(item)
    setattr(self, items_field, new_items)


def merge_same_items(items: list[_T]) -> list[_T]:
    """Merge items that have same Item Code."""
    counter = count_qty(items)
    new_items: list[SalesOrderItem] = []
    for item_code, cur_items in group_by_attr(items).items():
        cur_items[0].qty = counter[item_code]
        new_items.append(cur_items[0])
    return new_items
