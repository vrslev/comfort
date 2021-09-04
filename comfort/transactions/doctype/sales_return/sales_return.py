from __future__ import annotations

from copy import copy
from typing import Callable

import frappe
from comfort import ValidationError, count_quantity, group_by_attr
from comfort.entities.doctype.item.item import Item
from comfort.finance import create_gl_entry, get_account
from comfort.stock import create_stock_entry
from frappe import _
from frappe.model.document import Document

from ..sales_order.sales_order import SalesOrder
from ..sales_order_child_item.sales_order_child_item import SalesOrderChildItem
from ..sales_order_item.sales_order_item import SalesOrderItem
from ..sales_return_item.sales_return_item import SalesReturnItem


# TODO: Observe case when all items are returned
class SalesReturn(Document):
    sales_order: str
    returned_paid_amount: int
    items: list[SalesReturnItem]

    __voucher: SalesOrder | None = None

    @property
    def _voucher(self) -> SalesOrder:
        if not self.__voucher:
            self.__voucher: SalesOrder = frappe.get_doc("Sales Order", self.sales_order)
        return self.__voucher

    def delete_empty_items(self):
        if not hasattr(self, "items") or self.items is None:
            self.items = []
        items = copy(self.items)
        self.items = []
        for item in items:
            if item.qty != 0:
                self.items.append(item)

    def _validate_not_all_items_returned(self):
        if (
            len(
                [
                    i
                    for i in self._get_remaining_qtys(
                        self._voucher._get_items_with_splitted_combinations()
                    )
                ]
            )
            == 0
        ):
            raise ValidationError(_("Can't return all items in Sales Order"))

    def _validate_voucher_statuses(self):
        if self._voucher.docstatus != 1:
            raise ValidationError(_("Sales Order should be submitted"))
        elif self._voucher.delivery_status not in [
            "Purchased",
            "To Deliver",
            "Delivered",
        ]:
            raise ValidationError(
                _("Delivery Status should be Purchased, To Deliver or Delivered")
            )

    def _calculate_item_values(self):
        for item in self.items:
            item.amount = item.qty * item.rate

    def _calculate_returned_paid_amount(self):
        self._modify_voucher()
        self._voucher._set_paid_and_pending_per_amount()
        self.returned_paid_amount = (
            -copy(self._voucher.pending_amount)
            if self._voucher.pending_amount < 0
            else 0
        )
        self._voucher.reload()

    @frappe.whitelist()
    def calculate(self):  # pragma: no cover
        self._calculate_item_values()
        self._calculate_returned_paid_amount()

    def _get_remaining_qtys(
        self, items_in_voucher: list[SalesOrderItem | SalesOrderChildItem]
    ):
        in_order = count_quantity(items_in_voucher)
        in_return = count_quantity(self.items)
        for item in in_order:
            in_order[item] -= in_return.get(item, 0)
        return (item for item in in_order.items() if item[1] > 0)

    @frappe.whitelist()
    def get_items_available_to_add(self):
        self.delete_empty_items()
        items_in_order = self._voucher._get_items_with_splitted_combinations()
        _add_rates_to_child_items(items_in_order)
        available_item_and_qty = self._get_remaining_qtys(items_in_order)
        grouped_items = group_by_attr(items_in_order)

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
                self.calculate()
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

    def _split_combinations_in_voucher(self):
        return_qty_counter = count_quantity(self.items)
        items_no_children_qty_counter = count_quantity(self._voucher.items)
        parent_item_codes_to_modify: list[str] = []

        for c in self._voucher.child_items:
            qty_to_return = return_qty_counter.get(c.item_code)
            qty_in_items = items_no_children_qty_counter.get(c.item_code)

            if qty_to_return and (
                # Item is present in child items and in items but there's not enough qty
                (qty_in_items and qty_to_return > qty_in_items)
                # Item in child items and not in items
                or (not qty_in_items)
            ):
                parent_item_codes_to_modify.append(c.parent_item_code)

        if parent_item_codes_to_modify:
            self._voucher.set_name_in_children()  # Critical because in next step we use `item.name`
            self._voucher.split_combinations(
                [
                    item.name
                    for item in self._voucher.items
                    if item.item_code  # It is ok because we merge items in SO on validate
                    in parent_item_codes_to_modify
                ],
                save=False,
            )

    def _add_missing_info_to_items_in_voucher(self):  # TODO: Add `item_name`
        for item in self._voucher.items:
            if not item.rate or not item.weight:
                item.item_name, item.rate, item.weight = frappe.get_value(
                    "Item", item.item_code, ("item_name", "rate", "weight")
                )
                item.amount = item.qty * item.rate
                item.total_weight = item.qty * item.weight

    def _modify_voucher(self):
        self._split_combinations_in_voucher()

        qty_counter = count_quantity(self.items)
        for item in self._voucher.items:
            if item.item_code in qty_counter:
                item.qty -= qty_counter[item.item_code]
                del qty_counter[item.item_code]

        self._voucher.edit_commission = True
        # NOTE: Never use `update_items_from_db`
        self._voucher.delete_empty_items()
        self._voucher.merge_same_items()
        self._voucher.set_child_items()
        self._add_missing_info_to_items_in_voucher()
        self._voucher.calculate()

    def _modify_and_save_voucher(self):  # TODO: Cover
        self._modify_voucher()
        self._voucher.flags.ignore_validate_update_after_submit = True
        self._voucher.save()

    def _make_delivery_gl_entries(self):
        """Transfer cost of returned items from "Cost of Goods Sold" to "Inventory" account if Sales Order is delivered.
        Changes Sales Receipt behavior."""
        if not self._voucher.delivery_status == "Delivered":
            return
        prev_items_cost = copy(self._voucher.items_cost)
        self._modify_voucher()
        new_items_cost = copy(self._voucher.items_cost)
        self._voucher.reload()
        amount = prev_items_cost - new_items_cost
        create_gl_entry(
            self.doctype, self.name, get_account("cost_of_goods_sold"), 0, amount
        )
        create_gl_entry(self.doctype, self.name, get_account("inventory"), amount, 0)

    def _make_stock_entries(self):
        """Transfer returned items.

        Depends on `delivery_status`:
            "":          None
            To Purchase: None
            Purchased:   "Reserved Purchased" -> "Available Purchased" (change Checkout behavior)
            To Deliver:  "Reserved Actual"    -> "Available Actual"    (change Purchase Receipt behavior)
            Delivered:   "Reserved Actual"    -> "Available Actual"    (change Sales Receipt behavior)
        """
        status_to_stock_types = {
            "Purchased": ("Reserved Purchased", "Available Purchased"),
            "To Deliver": ("Reserved Actual", "Available Actual"),
            "Delivered": ("Reserved Actual", "Available Actual"),
        }
        if self._voucher.delivery_status not in status_to_stock_types.keys():
            return
        for stock_type in status_to_stock_types[self._voucher.delivery_status]:
            create_stock_entry(self.doctype, self.name, stock_type, self.items)

    def _make_payment_gl_entries(self):
        """Return `returned_paid_amount` from "Cash" or "Bank" -> "Sales".
        Changes Payment behavior.
        """
        if not self.returned_paid_amount:
            return
        paid_with_cash: bool | None = frappe.get_value(
            "Payment",
            fieldname="paid_with_cash",
            filters={"voucher_type": "Sales Order", "voucher_no": self.sales_order},
        )
        amt = self.returned_paid_amount
        asset_account = get_account("cash") if paid_with_cash else get_account("bank")
        create_gl_entry(self.doctype, self.name, asset_account, 0, amt)
        create_gl_entry(self.doctype, self.name, get_account("sales"), amt, 0)

    def validate(self):  # pragma: no cover
        self.delete_empty_items()
        self._validate_voucher_statuses()
        self._validate_not_all_items_returned()
        self.calculate()

    def before_submit(self):  # pragma: no cover
        self._modify_and_save_voucher()
        self._make_delivery_gl_entries()
        self._make_stock_entries()
        self._make_payment_gl_entries()

    def before_cancel(self):
        raise ValidationError(_("Not allowed to cancel Sales Return"))


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
