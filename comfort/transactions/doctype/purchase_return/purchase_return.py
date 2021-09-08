"""
Purchase Return modifications

Should return items to sell first, then sales order items
Statuses: ["To Receive", "Completed"]

*To Receive*
Change Payment and Checkout behavior

GL Entry:    Prepaid Inventory -> Cash/Bank
Stock Entry: Reserved Purchased -> None
             Available Purchased -> None


*Completed*
Change Payment, Checkout and Purchase Receipt behavior

GL Entry:    Inventory -> Cash/Bank
Stock Entry: Reserved Actual -> None
             Available Actual -> None



"""

# TODO: Modify Purchase Order's items to sell
from __future__ import annotations

from collections import defaultdict

import frappe
from comfort import ValidationError, count_quantity, group_by_attr
from comfort.entities.doctype.child_item.child_item import ChildItem
from comfort.entities.doctype.item.item import Item
from comfort.finance import create_gl_entry, get_account
from comfort.stock import create_stock_entry
from comfort.transactions import Return, _AnyItem, delete_empty_items, merge_same_items
from comfort.transactions.doctype.purchase_order_item_to_sell.purchase_order_item_to_sell import (
    PurchaseOrderItemToSell,
)
from comfort.transactions.doctype.sales_return.sales_return import SalesReturn
from frappe import _

from ..purchase_order.purchase_order import PurchaseOrder
from ..purchase_return_item.purchase_return_item import PurchaseReturnItem
from ..sales_order.sales_order import SalesOrder


class PurchaseReturn(Return):
    purchase_order: str
    returned_paid_amount: int
    items: list[PurchaseReturnItem]

    __voucher: PurchaseOrder | None = None

    @property
    def _voucher(self) -> PurchaseOrder:
        if not self.__voucher:
            self.__voucher: PurchaseOrder = frappe.get_doc(
                "Purchase Order", self.purchase_order
            )
        return self.__voucher

    def _calculate_returned_paid_amount(self):
        self.returned_paid_amount = 0
        for item in self.items:
            self.returned_paid_amount += item.qty * item.rate

    def _validate_voucher_statuses(self):
        if self._voucher.docstatus != 1:
            raise ValidationError(_("Purchase Order should be submitted"))

        if self._voucher.status not in ("To Receive", "Completed"):
            raise ValidationError(_("Status should be To Receive or Completed"))

    def _get_all_items(self):
        items: list[_AnyItem] = []
        items += self._voucher._get_items_to_sell(True)
        for sales_order in self._voucher.sales_orders:
            doc: SalesOrder = frappe.get_doc(
                "Sales Order", sales_order.sales_order_name
            )
            items += doc._get_items_with_splitted_combinations()
        return items

    def _allocate_items(self):
        orders_to_items: defaultdict[str | None, list[_AnyItem]] = defaultdict(list)

        def append_item(item: _AnyItem):
            item_dict = {
                "item_code": item.item_code,
                "item_name": item.item_name,
                "qty": item.qty,
                "rate": item.rate,
            }
            if item.get("doctype") in ("Sales Order Item", "Sales Order Child Item"):
                parent: str = item.parent
                orders_to_items[parent].append(item_dict)
            else:
                orders_to_items[None].append(item_dict)

        all_items = self._get_all_items()
        self._add_missing_fields_to_items(all_items)
        grouped_items = group_by_attr(all_items)
        for item_code, qty in count_quantity(self.items).items():
            for item in grouped_items[item_code]:
                if item.qty >= qty:
                    item.qty = qty
                    append_item(item)
                    break
                else:
                    append_item(item)
                    qty -= item.qty

        return orders_to_items

    def _add_missing_field_to_items_to_sell(
        self, items: list[PurchaseOrderItemToSell | ChildItem]
    ):
        def include(item: PurchaseOrderItemToSell | ChildItem):
            if (
                not item.get("rate")
                or not item.get("weight")
                or not item.get("item_name")
                or not item.get("amount")
            ):
                return True
            return False

        items_with_missing_fields: list[Item] = frappe.get_all(
            "Item",
            fields=("item_code", "item_name", "rate", "weight"),
            filters={"item_code": ("in", (i.item_code for i in items if include(i)))},
        )
        grouped_items = group_by_attr(items_with_missing_fields)

        for item in items:
            if item.item_code in grouped_items:
                grouped_item = grouped_items[item.item_code][0]
                item.item_name = grouped_item.item_name
                item.rate = grouped_item.rate
                item.weight = grouped_item.weight
            item.amount = item.qty * item.rate

    def _split_combinations_in_voucher(self):
        items = merge_same_items(self._voucher._get_items_to_sell(True))
        self._add_missing_field_to_items_to_sell(items)
        self._voucher.items_to_sell = []
        self._voucher.extend("items_to_sell", items)

    def _modify_voucher(self, orders_to_items: defaultdict[str | None, list[_AnyItem]]):
        self._split_combinations_in_voucher()
        qty_counter = count_quantity(
            frappe._dict(i) for i in orders_to_items[None]
        )  # TODO: Qty counter should be for items to sell, not global
        for item in self._voucher.items_to_sell:
            if item.item_code in qty_counter:
                item.qty -= qty_counter[item.item_code]
                del qty_counter[item.item_code]

        delete_empty_items(self._voucher, "items_to_sell")
        self._voucher.items_to_sell = merge_same_items(self._voucher.items_to_sell)
        # NOTE: Never use `update_items_to_sell_from_db`
        self._voucher.update_sales_orders_from_db()
        self._voucher.calculate()
        self._voucher.flags.ignore_validate_update_after_submit = True
        self._voucher.save()

    def _make_sales_returns(
        self, orders_to_items: defaultdict[str | None, list[_AnyItem]]
    ):
        for order_name, items in orders_to_items.items():
            if order_name is None:
                continue
            doc: SalesReturn = frappe.new_doc("Sales Return")
            doc.sales_order = order_name
            doc.from_purchase_return = self.name
            doc.extend("items", items)
            doc.insert()
            doc.submit()

    def _make_gl_entries(self):
        """Return `returned_paid_amount` to "Cash" or "Bank".
        "To Receive": from "Prepaid Inventory"
        "Completed": from "Inventory"
        """
        if not self.returned_paid_amount:
            return

        status_to_inventory_account = {
            "To Receive": "prepaid_inventory",
            "Completed": "inventory",
        }
        if self._voucher.status not in status_to_inventory_account.keys():
            return

        paid_with_cash: bool | None = frappe.get_value(
            "Payment",
            fieldname="paid_with_cash",
            filters={
                "voucher_type": "Purchase Order",
                "voucher_no": self.purchase_order,
            },
        )
        amt = self.returned_paid_amount
        asset_account = get_account("cash") if paid_with_cash else get_account("bank")
        inventory_account = get_account(
            status_to_inventory_account[self._voucher.status]
        )
        create_gl_entry(self.doctype, self.name, inventory_account, 0, amt)
        create_gl_entry(self.doctype, self.name, asset_account, amt, 0)

    def _make_stock_entries(self):
        """Return items to supplier.

        Since Sales Returns make Stock Entries (Reserved -> Available), making only (Available -> None)
        """
        stock_type = {
            "To Receive": "Available Purchased",
            "Completed": "Available Actual",
        }[self._voucher.status]
        create_stock_entry(
            self.doctype, self.name, stock_type, self.items, reverse_qty=True
        )

    def before_submit(self):  # pragma: no cover
        orders_to_items = self._allocate_items()
        self._make_sales_returns(orders_to_items)
        self._modify_voucher(orders_to_items)
        self._make_gl_entries()
        self._make_stock_entries()
