from __future__ import annotations

from collections import Counter
from types import SimpleNamespace
from typing import Any, Callable, TypedDict

import frappe
from comfort.entities import Item
from comfort.transactions.doctype.purchase_return_item.purchase_return_item import (
    PurchaseReturnItem,
)
from comfort.transactions.doctype.sales_return_item.sales_return_item import (
    SalesReturnItem,
)
from comfort.transactions.utils import delete_empty_items, merge_same_items
from comfort.utils import (
    TypedDocument,
    ValidationError,
    _,
    count_qty,
    get_all,
    group_by_attr,
)


class _ReturnAddItemsPayloadItem(TypedDict):
    item_code: str
    item_name: str | None
    qty: int
    rate: int


class Return(TypedDocument):
    returned_paid_amount: int
    items: list[SalesReturnItem] | list[PurchaseReturnItem]

    @property
    def _voucher(self) -> Any:  # pragma: no cover
        pass

    def _calculate_returned_paid_amount(self):  # pragma: no cover
        pass

    def _validate_voucher_statuses(self):  # pragma: no cover
        pass

    def _get_all_items(self) -> Any:  # pragma: no cover
        pass

    def delete_empty_items(self):
        if not hasattr(self, "items") or self.items is None:
            self.items = []
        delete_empty_items(self, "items")

    def _calculate_item_values(self):
        for item in self.items:
            item.amount = item.qty * item.rate

    @frappe.whitelist()
    def calculate(self):
        self._calculate_item_values()
        self._calculate_returned_paid_amount()

    def _get_remaining_qtys(self, items: list[Any]):
        in_voucher = count_qty(items)
        in_return = count_qty(self.items)
        for item in in_voucher:
            in_voucher[item] -= in_return.get(item, 0)
        return (item for item in in_voucher.items() if item[1] > 0)

    def _add_missing_fields_to_items(self, items: list[Any]):
        items_with_missing_fields = get_all(
            Item,
            field=("item_code", "item_name", "rate"),
            filter={
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

        res: list[_ReturnAddItemsPayloadItem] = [
            {
                "item_code": item_code,
                "item_name": grouped_items[item_code][0].item_name,
                "qty": qty,
                "rate": grouped_items[item_code][0].rate,
            }
            for item_code, qty in available_item_and_qty
        ]
        sort_by: Callable[[Any], str | None] = lambda i: i["item_name"]
        res.sort(key=sort_by)
        return res

    def _validate_new_item(
        self, counter: Counter[str], item: _ReturnAddItemsPayloadItem
    ):
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
    def add_items(self, items: list[_ReturnAddItemsPayloadItem]):
        all_items = self.get_items_available_to_add()
        counter = count_qty(SimpleNamespace(**item) for item in all_items)

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

    def validate(self):
        self.delete_empty_items()
        self._validate_voucher_statuses()
        self._validate_not_all_items_returned()
        self.calculate()
