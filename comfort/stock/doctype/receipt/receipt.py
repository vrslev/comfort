from __future__ import annotations

from typing import Any

import frappe
from comfort import count_qty
from comfort.entities.doctype.child_item.child_item import ChildItem
from comfort.finance import cancel_gl_entries_for, create_gl_entry, get_account
from comfort.stock import cancel_stock_entries_for, create_stock_entry
from comfort.transactions import OrderTypes
from comfort.transactions.doctype.purchase_order.purchase_order import PurchaseOrder
from comfort.transactions.doctype.purchase_order_item_to_sell.purchase_order_item_to_sell import (
    PurchaseOrderItemToSell,
)
from comfort.transactions.doctype.sales_order.sales_order import SalesOrder
from comfort.transactions.doctype.sales_order_child_item.sales_order_child_item import (
    SalesOrderChildItem,
)
from comfort.transactions.doctype.sales_order_item.sales_order_item import (
    SalesOrderItem,
)
from frappe.model.document import Document

from ..stock_entry.stock_entry import StockTypes


class Receipt(Document):
    voucher_type: OrderTypes
    voucher_no: str

    __voucher: SalesOrder | PurchaseOrder | None = None

    @property
    def _voucher(self) -> SalesOrder | PurchaseOrder:
        if not self.__voucher:
            self.__voucher = frappe.get_doc(self.voucher_type, self.voucher_no)
        return self.__voucher

    def _new_gl_entry(self, account_field: str, debit: int, credit: int):
        create_gl_entry(
            self.doctype, self.name, get_account(account_field), debit, credit
        )

    def _new_stock_entry(
        self,
        stock_type: StockTypes,
        items: list[Any],
        reverse_qty: bool = False,  # TODO: Cover
    ):
        create_stock_entry(self.doctype, self.name, stock_type, items, reverse_qty)

    def before_submit(self):  # pragma: no cover
        if self.voucher_type == "Sales Order":
            self.create_sales_gl_entries()
            self.create_sales_stock_entries()
        elif self.voucher_type == "Purchase Order":
            self.create_purchase_gl_entries()
            self.create_purchase_stock_entries()

    def on_cancel(self):  # pragma: no cover
        # TODO: Need to transfer items to available if Sales Order is cancelled
        cancel_gl_entries_for(self.doctype, self.name)
        cancel_stock_entries_for(self.doctype, self.name)
        self.set_status_in_sales_order()

    def create_sales_gl_entries(self):
        items_cost: int = self._voucher.items_cost
        self._new_gl_entry("inventory", 0, items_cost)
        self._new_gl_entry("cost_of_goods_sold", items_cost, 0)

    def create_sales_stock_entries(self):
        items_obj: list[
            SalesOrderItem | SalesOrderChildItem
        ] = self._voucher._get_items_with_splitted_combinations()
        items = [
            frappe._dict({"item_code": item_code, "qty": -qty})
            for item_code, qty in count_qty(items_obj).items()
        ]
        self._new_stock_entry("Reserved Actual", items)

    def create_purchase_gl_entries(self):
        items_amount: int = frappe.get_value(
            self.voucher_type,
            self.voucher_no,
            "items_to_sell_cost + sales_orders_cost as items_amount",
        )
        self._new_gl_entry("prepaid_inventory", 0, items_amount)
        self._new_gl_entry("inventory", items_amount, 0)

    def _create_purchase_stock_entries_for_sales_orders(self):
        items_obj: list[
            SalesOrderItem | SalesOrderChildItem
        ] = self._voucher._get_items_in_sales_orders(split_combinations=True)
        if not items_obj:
            return

        items = [
            frappe._dict({"item_code": i.item_code, "qty": i.qty}) for i in items_obj
        ]
        self._new_stock_entry("Reserved Purchased", items, reverse_qty=True)
        self._new_stock_entry("Reserved Actual", items)

    def _create_purchase_stock_entries_for_items_to_sell(self):
        items_obj: list[
            PurchaseOrderItemToSell | ChildItem
        ] = self._voucher._get_items_to_sell(split_combinations=True)
        if not items_obj:
            return

        items: dict[str, str | int] = [  # TODO: is this necessary?
            frappe._dict({"item_code": i.item_code, "qty": i.qty}) for i in items_obj
        ]
        self._new_stock_entry("Available Purchased", items, reverse_qty=True)
        self._new_stock_entry("Available Actual", items)

    def create_purchase_stock_entries(self):  # pragma: no cover
        self._create_purchase_stock_entries_for_sales_orders()
        self._create_purchase_stock_entries_for_items_to_sell()

    def set_status_in_sales_order(self):
        if self.voucher_type == "Sales Order":
            doc: SalesOrder = frappe.get_doc(self.voucher_type, self.voucher_no)
            doc.set_statuses()
            doc.db_update()
