from __future__ import annotations

from copy import deepcopy
from typing import Any

import frappe
from comfort import OrderTypes, count_quantity
from comfort.entities.doctype.child_item.child_item import ChildItem
from comfort.finance import get_account
from comfort.finance.doctype.gl_entry.gl_entry import GLEntry
from comfort.transactions.doctype.purchase_order_item_to_sell.purchase_order_item_to_sell import (
    PurchaseOrderItemToSell,
)
from comfort.transactions.doctype.sales_order_child_item.sales_order_child_item import (
    SalesOrderChildItem,
)
from comfort.transactions.doctype.sales_order_item.sales_order_item import (
    SalesOrderItem,
)
from frappe.model.document import Document

from ..stock_entry.stock_entry import StockEntry, _StockType
from ..stock_entry_item.stock_entry_item import StockEntryItem


class Receipt(Document):
    voucher_type: OrderTypes
    voucher_no: str
    __voucher: Document

    @property
    def _voucher(self) -> Document:
        if not hasattr(self, "__voucher"):
            self.__voucher = frappe.get_doc(self.voucher_type, self.voucher_no)
        return self.__voucher

    def _new_gl_entry(self, account_field: str, debit: int, credit: int):
        GLEntry.create_for(
            self.doctype, self.name, get_account(account_field), debit, credit
        )

    def _new_stock_entry(self, stock_type: _StockType, items: list[StockEntryItem]):
        StockEntry.create_for(self.doctype, self.name, stock_type, items)

    def before_submit(self):  # pragma: no cover
        if self.voucher_type == "Sales Order":
            self.create_sales_gl_entries()
            self.create_sales_stock_entries()
        elif self.voucher_type == "Purchase Order":
            self.create_purchase_gl_entries()
            self.create_purchase_stock_entries()

    def before_cancel(self):  # pragma: no cover
        # TODO: Need to transfer items to available if Sales Order is cancelled
        GLEntry.cancel_for(self.doctype, self.name)
        StockEntry.cancel_for(self.doctype, self.name)

    @staticmethod
    def create_for(doctype: OrderTypes, name: str):  # pragma: no cover
        doc: Receipt = frappe.get_doc(
            {"doctype": "Receipt", "voucher_type": doctype, "voucher_no": name}
        )
        doc.insert()
        doc.submit()
        return doc

    # Sales Order

    def create_sales_gl_entries(self):
        items_cost: int = self._voucher.items_cost
        self._new_gl_entry("inventory", 0, items_cost)
        self._new_gl_entry("cost_of_goods_sold", items_cost, 0)

    def _get_sales_order_items_with_splitted_combinations(
        self,
    ) -> list[SalesOrderChildItem | SalesOrderItem]:
        parents = (child.parent_item_code for child in self._voucher.child_items)
        return self._voucher.child_items + [
            item for item in self._voucher.items if item.item_code not in parents
        ]

    def create_sales_stock_entries(self):
        items = [
            {"item_code": item_code, "qty": -qty}
            for item_code, qty in count_quantity(
                self._get_sales_order_items_with_splitted_combinations()
            ).items()
        ]
        self._new_stock_entry("Reserved Actual", items)

    # Purchase Order

    def create_purchase_gl_entries(self):
        items_amount = frappe.get_value(
            self.voucher_type,
            self.voucher_no,
            "items_to_sell_cost + sales_order_cost as items_amount",
        )
        self._new_gl_entry("prepaid_inventory", 0, items_amount)
        self._new_gl_entry("inventory", items_amount, 0)

    def create_purchase_stock_entries(self):  # pragma: no cover
        self._create_purchase_stock_entries_for_sales_orders()
        self._create_purchase_stock_entries_for_items_to_sell()

    def _get_items_with_reversed_qty(
        self, items: list[dict[str, Any]]
    ):  # pragma: no cover
        reverse_items = deepcopy(items)
        for item in reverse_items:
            item["qty"] = -item["qty"]
        return reverse_items

    def _create_purchase_stock_entries_for_sales_orders(self):
        items_obj: list[
            SalesOrderItem | SalesOrderChildItem
        ] = self._voucher._get_items_in_sales_orders(split_combinations=True)
        if not items_obj:
            return

        items = [{"item_code": i.item_code, "qty": i.qty} for i in items_obj]
        reverse_items = self._get_items_with_reversed_qty(items)

        self._new_stock_entry("Reserved Purchased", reverse_items)
        self._new_stock_entry("Reserved Actual", items)

    def _create_purchase_stock_entries_for_items_to_sell(self):
        items_obj: list[
            PurchaseOrderItemToSell | ChildItem
        ] = self._voucher._get_items_to_sell(split_combinations=True)
        if not items_obj:
            return

        items: dict[str, str | int] = [
            {"item_code": i.item_code, "qty": i.qty} for i in items_obj
        ]
        reverse_items = self._get_items_with_reversed_qty(items)

        self._new_stock_entry("Available Purchased", reverse_items)
        self._new_stock_entry("Available Actual", items)
