from __future__ import annotations

from copy import copy
from typing import Literal

from comfort import (
    ValidationError,
    _,
    count_qty,
    get_all,
    get_doc,
    get_value,
    group_by_attr,
)
from comfort.entities.doctype.item.item import Item
from comfort.finance import cancel_gl_entries_for, create_gl_entry, get_account
from comfort.stock import cancel_stock_entries_for, create_stock_entry
from comfort.transactions import Return, delete_empty_items, merge_same_items
from comfort.transactions.doctype.purchase_order.purchase_order import PurchaseOrder
from comfort.transactions.doctype.purchase_order_item_to_sell.purchase_order_item_to_sell import (
    PurchaseOrderItemToSell,
)

from ..sales_order.sales_order import SalesOrder
from ..sales_return_item.sales_return_item import SalesReturnItem


class SalesReturn(Return):
    doctype: Literal["Sales Return"]

    sales_order: str
    returned_paid_amount: int
    items: list[SalesReturnItem]
    from_purchase_return: str

    __voucher: SalesOrder | None = None

    @property
    def _voucher(self) -> SalesOrder:
        if not self.__voucher:
            self.__voucher = get_doc(SalesOrder, self.sales_order)
        return self.__voucher

    def _calculate_returned_paid_amount(self):
        self._modify_voucher()
        self._voucher.set_paid_and_pending_per_amount()
        self.returned_paid_amount = (
            -copy(self._voucher.pending_amount)
            if self._voucher.pending_amount < 0
            else 0
        )
        self._voucher.reload()

    def _validate_voucher_statuses(self):
        if self.flags.sales_order_on_cancel:
            return

        if self._voucher.docstatus != 1:
            raise ValidationError(_("Sales Order should be submitted"))
        elif self._voucher.delivery_status not in (
            "Purchased",
            "To Deliver",
            "Delivered",
        ):
            raise ValidationError(
                _("Delivery Status should be Purchased, To Deliver, or Delivered")
            )

    def _validate_not_all_items_returned(self):
        pass

    def _get_all_items(self):
        return self._voucher.get_items_with_splitted_combinations()

    def _split_combinations_in_voucher(self):
        return_qty_counter = count_qty(self.items)
        items_no_children_qty_counter = count_qty(self._voucher.items)
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
                item_values: tuple[str, int, float] = get_value(
                    "Item", item.item_code, ("item_name", "rate", "weight")
                )
                item.item_name, item.rate, item.weight = item_values

                item.amount = item.qty * item.rate
                item.total_weight = item.qty * item.weight

    def _modify_voucher(self):
        self._split_combinations_in_voucher()

        qty_counter = count_qty(self.items)
        for item in self._voucher.items:
            if item.item_code in qty_counter:
                item.qty -= qty_counter[item.item_code]
                del qty_counter[item.item_code]

        self._voucher.edit_commission = True
        # NOTE: Never use `update_items_from_db`
        delete_empty_items(self._voucher, "items")
        self._voucher.items = merge_same_items(self._voucher.items)
        self._voucher.set_child_items()
        self._add_missing_info_to_items_in_voucher()
        self._voucher.calculate()

    def _add_missing_info_to_items_in_items_to_sell(
        self, items: list[PurchaseOrderItemToSell]
    ):
        items_with_weight = get_all(
            Item,
            fields=("item_code", "weight"),
            filters={"item_code": ("in", (i.item_code for i in items if not i.weight))},
        )
        grouped_items = group_by_attr(items_with_weight)
        for item in items:
            if item.item_code in grouped_items:
                item.weight = grouped_items[item.item_code][0].weight
            item.amount = item.rate * item.qty

    def _add_items_to_sell_to_linked_purchase_order(self):
        purchase_order_name: str | None = get_value(
            "Purchase Order Sales Order",
            filters={"sales_order_name": self._voucher.name, "docstatus": ("!=", 2)},
            fieldname="parent",
        )
        if purchase_order_name is None:
            # If Sales Order is from Available Actual stock
            # then it is not linked to any Purchase Order
            return
        doc = get_doc(PurchaseOrder, purchase_order_name)
        doc.extend(
            "items_to_sell",
            [
                {
                    "item_code": i.item_code,
                    "item_name": i.item_name,
                    "qty": i.qty,
                    "rate": i.rate,
                }
                for i in self.items
            ],
        )
        doc.items_to_sell = merge_same_items(doc.items_to_sell)
        self._add_missing_info_to_items_in_items_to_sell(doc.items_to_sell)
        doc.flags.ignore_validate_update_after_submit = True
        doc.flags.ignore_links = True
        doc.save()

    def _make_delivery_gl_entries(self):
        """Transfer cost of returned items from "Prepaid Sales" to "Inventory" account if Sales Order is delivered.
        Changes Sales Receipt behavior."""
        if not self._voucher.delivery_status == "Delivered":
            return
        prev_items_cost = copy(self._voucher.items_cost)
        self._modify_voucher()
        new_items_cost = copy(self._voucher.items_cost)
        self._voucher.reload()
        amount = prev_items_cost - new_items_cost
        create_gl_entry(
            self.doctype, self.name, get_account("prepaid_sales"), 0, amount
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
        if self._voucher.delivery_status not in (
            "Purchased",
            "To Deliver",
            "Delivered",
        ):
            return

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
        """Return `returned_paid_amount` from "Cash" or "Bank" to "Prepaid Sales".
        Changes Payment behavior.
        """
        if not self.returned_paid_amount:
            return
        paid_with_cash: bool | None = get_value(
            "Payment",
            fieldname="paid_with_cash",
            filters={"voucher_type": "Sales Order", "voucher_no": self.sales_order},
        )
        amt = self.returned_paid_amount
        asset_account = "cash" if paid_with_cash else "bank"
        create_gl_entry(self.doctype, self.name, get_account(asset_account), 0, amt)
        create_gl_entry(self.doctype, self.name, get_account("prepaid_sales"), amt, 0)

    def before_submit(self):
        self._modify_voucher()

        return_all_items = len(self._voucher.items) == 0
        if return_all_items:
            self._voucher.reload()
        else:
            self._voucher.flags.ignore_validate_update_after_submit = True
            self._voucher.save()

        self._make_delivery_gl_entries()
        self._make_stock_entries()
        self._make_payment_gl_entries()

        if return_all_items:
            self._voucher.flags.on_cancel_from_sales_return = True
            self._voucher.cancel()

        self._add_items_to_sell_to_linked_purchase_order()

    def before_cancel(self):
        if not self.flags.from_purchase_return:
            raise ValidationError(_("Not allowed to cancel Sales Return"))

    def on_cancel(self):
        cancel_gl_entries_for(self.doctype, self.name)
        cancel_stock_entries_for(self.doctype, self.name)
