from __future__ import annotations

from typing import TYPE_CHECKING, Any, Literal

import frappe
from comfort.finance.utils import cancel_gl_entries_for, create_gl_entry, get_account
from comfort.stock.doctype.stock_entry.stock_entry import StockTypes
from comfort.stock.utils import cancel_stock_entries_for, create_stock_entry
from comfort.utils import TypedDocument, ValidationError, _, get_doc, get_value

if TYPE_CHECKING:
    from comfort.transactions import PurchaseOrder, SalesOrder


class Receipt(TypedDocument):
    doctype: Literal["Receipt"]
    voucher_type: Literal["Sales Order", "Purchase Order"]
    voucher_no: str

    __voucher: SalesOrder | PurchaseOrder | None = None

    @property
    def _voucher(self) -> SalesOrder | PurchaseOrder:
        if not self.__voucher:
            self.__voucher = frappe.get_doc(self.voucher_type, self.voucher_no)  # type: ignore
        return self.__voucher  # type: ignore

    def _new_gl_entry(self, account_field: str, debit: int, credit: int) -> None:
        create_gl_entry(
            self.doctype, self.name, get_account(account_field), debit, credit
        )

    def _new_stock_entry(
        self,
        stock_type: StockTypes,
        items: list[Any],
        reverse_qty: bool = False,
    ) -> None:
        create_stock_entry(self.doctype, self.name, stock_type, items, reverse_qty)

    def before_submit(self) -> None:  # pragma: no cover
        if self.voucher_type == "Sales Order":
            self.create_sales_gl_entries()
            self.create_sales_stock_entries()
        elif self.voucher_type == "Purchase Order":
            self.create_purchase_gl_entries()
            self.create_purchase_stock_entries()

    def on_cancel(self) -> None:
        cancel_gl_entries_for(self.doctype, self.name)
        cancel_stock_entries_for(self.doctype, self.name)
        self.set_status_in_voucher()

    def create_sales_gl_entries(self):
        from comfort.transactions import SalesOrderService

        inventory_amount: int = self._voucher.items_cost  # type: ignore
        sales_amount: int = self._voucher.margin - self._voucher.discount  # type: ignore
        delivery_amount, installation_amount = 0, 0
        prepaid_sales_amount: int = self._voucher.total_amount
        services: list[SalesOrderService] = self._voucher.services  # type: ignore
        for s in services:
            if "Delivery" in s.type:
                delivery_amount += s.rate
            elif "Installation" in s.type:
                installation_amount += s.rate
            else:
                raise ValidationError(_("Cannot calculate services amount for Receipt"))

        if inventory_amount:  # TODO: Test all this ifs
            self._new_gl_entry("inventory", 0, inventory_amount)
        if sales_amount:
            self._new_gl_entry("sales", 0, sales_amount)
        if delivery_amount:
            self._new_gl_entry("delivery", 0, delivery_amount)
        if installation_amount:
            self._new_gl_entry("installation", 0, installation_amount)
        if prepaid_sales_amount:
            self._new_gl_entry("prepaid_sales", prepaid_sales_amount, 0)

    def create_sales_stock_entries(self) -> None:
        items: Any = self._voucher.get_items_with_splitted_combinations()  # type: ignore
        self._new_stock_entry("Reserved Actual", items, reverse_qty=True)

    def create_purchase_gl_entries(self) -> None:
        items_amount: int = get_value(
            self.voucher_type,
            self.voucher_no,
            "items_to_sell_cost + sales_orders_cost as items_amount",
        )
        self._new_gl_entry("prepaid_inventory", 0, items_amount)
        self._new_gl_entry("inventory", items_amount, 0)

    def _create_purchase_stock_entries_for_sales_orders(self) -> None:
        items: Any = self._voucher.get_items_in_sales_orders(  # type: ignore
            split_combinations=True
        )
        if not items:
            return
        self._new_stock_entry("Reserved Purchased", items, reverse_qty=True)
        self._new_stock_entry("Reserved Actual", items)

    def _create_purchase_stock_entries_for_items_to_sell(self) -> None:
        items: list[Any] = self._voucher.get_items_to_sell(  # type: ignore
            split_combinations=True
        )
        if not items:
            return
        self._new_stock_entry("Available Purchased", items, reverse_qty=True)
        self._new_stock_entry("Available Actual", items)

    def create_purchase_stock_entries(self) -> None:  # pragma: no cover
        self._create_purchase_stock_entries_for_sales_orders()
        self._create_purchase_stock_entries_for_items_to_sell()

    def set_status_in_voucher(self) -> None:
        from comfort.transactions import PurchaseOrder, SalesOrder

        if self.voucher_type == "Sales Order":
            doc = get_doc(SalesOrder, self.voucher_no)
            doc.set_statuses()
            doc.save_without_validating()
        else:
            doc = get_doc(PurchaseOrder, self.voucher_no)
            doc.status = "To Receive"
            doc.save_without_validating()


def on_doctype_update() -> None:
    frappe.db.add_index("Receipt", ["voucher_type", "voucher_no"])
