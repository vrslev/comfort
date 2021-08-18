from __future__ import annotations

from typing import Any

import frappe
from comfort import OrderTypes, ValidationError
from comfort.finance import get_account
from frappe import _
from frappe.model.document import Document

from ..gl_entry.gl_entry import GLEntry


class Payment(Document):
    voucher_type: OrderTypes
    voucher_no: str
    amount: int
    paid_with_cash: bool
    _voucher: Document

    def validate(self):
        self.validate_amount_more_than_zero()

    def validate_amount_more_than_zero(self):
        if self.amount <= 0:
            raise ValidationError(_("Amount should be more that zero"))

    def _new_gl_entry(self, account_field: str, debit: int, credit: int):
        GLEntry.create_for(
            self.doctype, self.name, get_account(account_field), debit, credit
        )

    def _get_amounts_for_sales_gl_entries(self) -> dict[str, int]:
        self._voucher = frappe.get_doc(self.voucher_type, self.voucher_no)

        sales_amount = self._voucher.total_amount - self._voucher.service_amount
        delivery_amount, installation_amount = 0, 0

        for s in self._voucher.services:
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
        account_field = "cash" if self.paid_with_cash else "bank"
        self._new_gl_entry(account_field, self.amount, 0)

    def create_sales_gl_entries(self):
        amounts = self._get_amounts_for_sales_gl_entries()
        self._create_categories_sales_gl_entries(**amounts)
        self._create_income_sales_gl_entry()

    def create_purchase_gl_entries(self):
        cash_or_bank = "cash" if self.paid_with_cash else "bank"
        sums: Any = frappe.get_value(
            self.voucher_type,
            self.voucher_no,
            fields=[
                "sales_order_cost + items_to_sell_cost as prepaid_inventory",
                "delivery_cost as purchase_delivery",
            ],
        )

        self._new_gl_entry(cash_or_bank, 0, sums.prepaid_inventory)
        self._new_gl_entry("prepaid_inventory", sums.prepaid_inventory, 0)

        if sums.purchase_delivery > 0:
            self._new_gl_entry(cash_or_bank, 0, sums.purchase_delivery)
            self._new_gl_entry("purchase_delivery", sums.purchase_delivery, 0)

    def create_gl_entries(self):
        if self.voucher_type == "Sales Order":
            self.create_sales_gl_entries()
        elif self.voucher_type == "Purchase Order":
            self.create_purchase_gl_entries()

    def before_submit(self):
        self.create_gl_entries()

    def cancel_gl_entries(self):
        GLEntry.cancel_for(self.doctype, self.name)

    def before_cancel(self):
        self.cancel_gl_entries()

    @staticmethod
    def create_for(
        doctype: str, name: str, amount: int, paid_with_cash: bool
    ):  # pragma: no cover

        doc: Payment = frappe.get_doc(
            {
                "doctype": "Payment",
                "voucher_type": doctype,
                "voucher_no": name,
                "amount": amount,
                "paid_with_cash": paid_with_cash,
            }
        )
        doc.insert()
        doc.submit()
        return doc
