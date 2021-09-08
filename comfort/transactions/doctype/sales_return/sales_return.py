from __future__ import annotations

from copy import copy

import frappe
from comfort import ValidationError, count_quantity
from comfort.finance import create_gl_entry, get_account
from comfort.stock import create_stock_entry
from comfort.transactions import Return
from frappe import _

from ..sales_order.sales_order import SalesOrder
from ..sales_return_item.sales_return_item import SalesReturnItem


class SalesReturn(Return):
    sales_order: str
    returned_paid_amount: int
    items: list[SalesReturnItem]
    from_purchase_return: str

    __voucher: SalesOrder | None = None

    @property
    def _voucher(self) -> SalesOrder:
        if not self.__voucher:
            self.__voucher: SalesOrder = frappe.get_doc("Sales Order", self.sales_order)
        return self.__voucher

    def _calculate_returned_paid_amount(self):  # TODO: Why is this not used?
        self._modify_voucher()
        self._voucher._set_paid_and_pending_per_amount()
        self.returned_paid_amount = (
            -copy(self._voucher.pending_amount)
            if self._voucher.pending_amount < 0
            else 0
        )
        self._voucher.reload()

    def _validate_voucher_statuses(self):
        if self._voucher.docstatus != 1:
            raise ValidationError(_("Sales Order should be submitted"))
        elif self._voucher.delivery_status not in (
            "Purchased",
            "To Deliver",
            "Delivered",
        ):
            raise ValidationError(
                _("Delivery Status should be Purchased, To Deliver or Delivered")
            )

    def _get_all_items(self):
        return self._voucher._get_items_with_splitted_combinations()

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

    def _add_missing_info_to_items_in_voucher(self):
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

    def _modify_and_save_voucher(self):
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
        stock_types = {
            "Purchased": ("Reserved Purchased", "Available Purchased"),
            "To Deliver": ("Reserved Actual", "Available Actual"),
            "Delivered": ("Reserved Actual", "Available Actual"),
        }[self._voucher.delivery_status]
        create_stock_entry(
            self.doctype, self.name, stock_types[0], self.items, reverse_qty=True
        )
        create_stock_entry(self.doctype, self.name, stock_types[1], self.items)

    def _make_payment_gl_entries(self):
        """Return `returned_paid_amount` from "Cash" or "Bank" to "Sales".
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

    def before_submit(self):  # pragma: no cover
        self._modify_and_save_voucher()
        self._make_delivery_gl_entries()
        self._make_stock_entries()
        self._make_payment_gl_entries()
