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

from __future__ import annotations

from collections import defaultdict

import frappe
from comfort import ValidationError, count_quantity, group_by_attr
from comfort.finance import create_gl_entry, get_account
from comfort.stock import create_stock_entry
from comfort.transactions import Return, _AnyItem
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

        return orders_to_items.items()

    def _make_sales_returns(self):
        for order_name, items in self._allocate_items():
            if order_name is None:
                continue
            doc: SalesReturn = frappe.new_doc("Sales Return")
            doc.sales_order = order_name
            doc.extend("items", items)
            doc.save()
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
        """Return items to supplier."""
        stock_type = {
            "To Receive": "Available Purchased",
            "Completed": "Available Actual",
        }[self._voucher.status]
        create_stock_entry(
            self.doctype, self.name, stock_type, self.items, reverse_qty=True
        )

    def before_submit(self):  # pragma: no cover
        self._make_sales_returns()
        self._make_gl_entries()
        self._make_stock_entries()
