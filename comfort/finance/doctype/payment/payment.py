from __future__ import annotations

import frappe
from comfort import ValidationError
from comfort.finance import cancel_gl_entries_for, create_gl_entry, get_account
from comfort.transactions import OrderTypes
from comfort.transactions.doctype.sales_order.sales_order import SalesOrder
from frappe import _
from frappe.model.document import Document

# TODO: Allow to change Cash/Bank after submit


class Payment(Document):
    voucher_type: OrderTypes
    voucher_no: str
    amount: int
    paid_with_cash: bool

    def validate(self):
        if self.amount <= 0:
            raise ValidationError(_("Amount should be more that zero"))

    def _new_gl_entry(self, account_field: str, debit: int, credit: int):
        create_gl_entry(
            self.doctype, self.name, get_account(account_field), debit, credit
        )

    def _resolve_cash_or_bank(self):
        return "cash" if self.paid_with_cash else "bank"

    def _get_amounts_for_sales_gl_entries(self) -> dict[str, int]:
        doc: SalesOrder = frappe.get_doc(self.voucher_type, self.voucher_no)

        sales_amount: int = doc.total_amount - doc.service_amount
        delivery_amount, installation_amount = 0, 0

        for s in doc.services:
            if "Delivery" in s.type:
                delivery_amount += s.rate
            elif "Installation" in s.type:
                installation_amount += s.rate

        return {
            "sales_amount": sales_amount,
            "delivery_amount": delivery_amount,
            "installation_amount": installation_amount,
        }

    def _create_categories_sales_gl_entries(
        self,
        sales_amount: int,
        delivery_amount: int,
        installation_amount: int,
    ):
        remaining_amount = self.amount
        for accounts_name, amount in (
            ("sales", sales_amount),
            ("delivery", delivery_amount),
            ("installation", installation_amount),
        ):
            if amount == 0:
                continue

            elif amount > remaining_amount:
                self._new_gl_entry(accounts_name, 0, remaining_amount)
                remaining_amount = 0
                break

            else:
                self._new_gl_entry(accounts_name, 0, amount)
                remaining_amount -= amount

        if remaining_amount > 0:
            self._new_gl_entry("sales", 0, remaining_amount)

    def _create_income_sales_gl_entry(self):
        account_field = self._resolve_cash_or_bank()
        self._new_gl_entry(account_field, self.amount, 0)

    def create_sales_gl_entries(self):  # pragma: no cover
        amounts = self._get_amounts_for_sales_gl_entries()
        self._create_categories_sales_gl_entries(**amounts)
        self._create_income_sales_gl_entry()

    def create_purchase_gl_entries(self):
        cash_or_bank = self._resolve_cash_or_bank()
        values: tuple[int, int] = frappe.get_value(
            self.voucher_type,
            self.voucher_no,
            fieldname=(
                "sales_orders_cost + items_to_sell_cost as prepaid_inventory",
                "delivery_cost as purchase_delivery",
            ),
        )
        prepaid_inventory, purchase_delivery = values

        self._new_gl_entry(cash_or_bank, 0, prepaid_inventory)
        self._new_gl_entry("prepaid_inventory", prepaid_inventory, 0)

        if purchase_delivery > 0:
            self._new_gl_entry(cash_or_bank, 0, purchase_delivery)
            self._new_gl_entry("purchase_delivery", purchase_delivery, 0)

    def create_gl_entries(self):  # pragma: no cover
        if self.voucher_type == "Sales Order":
            self.create_sales_gl_entries()
        elif self.voucher_type == "Purchase Order":
            self.create_purchase_gl_entries()

    def before_submit(self):  # pragma: no cover
        self.create_gl_entries()

    def cancel_gl_entries(self):  # pragma: no cover
        cancel_gl_entries_for(self.doctype, self.name)

    def set_status_in_sales_order(self):
        if self.voucher_type == "Sales Order":
            doc: SalesOrder = frappe.get_doc(self.voucher_type, self.voucher_no)
            doc.set_statuses()
            doc.db_update()

    def on_cancel(self):  # pragma: no cover
        self.cancel_gl_entries()
        self.set_status_in_sales_order()
