from __future__ import annotations

from typing import Literal

from comfort import TypedDocument, ValidationError, _, get_doc, get_value
from comfort.finance.utils import cancel_gl_entries_for, create_gl_entry, get_account


class Payment(TypedDocument):
    doctype: Literal["Payment"]

    voucher_type: Literal["Sales Order", "Purchase Order"]
    voucher_no: str
    amount: int
    paid_with_cash: bool

    def validate(self):
        if self.amount <= 0:
            raise ValidationError(_("Amount should be more that zero"))

    def _new_gl_entry(self, account_field: str, debit: int, credit: int):
        create_gl_entry(
            doctype=self.doctype,
            name=self.name,
            account=get_account(account_field),
            debit=debit,
            credit=credit,
        )

    def _resolve_cash_or_bank(self):
        return "cash" if self.paid_with_cash else "bank"

    def create_sales_gl_entries(self):
        cash_or_bank = self._resolve_cash_or_bank()
        self._new_gl_entry(cash_or_bank, self.amount, 0)
        self._new_gl_entry("prepaid_sales", 0, self.amount)

    def _get_purchase_values(self) -> tuple[int, int]:
        fields = (
            "sales_orders_cost + items_to_sell_cost as prepaid_inventory",
            "delivery_cost as purchase_delivery",
        )
        return get_value(self.voucher_type, self.voucher_no, fieldname=fields)

    def create_purchase_gl_entries(self):
        prepaid_inventory, purchase_delivery = self._get_purchase_values()
        cash_or_bank = self._resolve_cash_or_bank()

        self._new_gl_entry(cash_or_bank, 0, prepaid_inventory)
        self._new_gl_entry("prepaid_inventory", prepaid_inventory, 0)

        if purchase_delivery > 0:
            self._new_gl_entry(cash_or_bank, 0, purchase_delivery)
            self._new_gl_entry("purchase_delivery", purchase_delivery, 0)

    def before_submit(self):
        if self.voucher_type == "Sales Order":
            self.create_sales_gl_entries()
        elif self.voucher_type == "Purchase Order":
            self.create_purchase_gl_entries()

    def set_status_in_sales_order(self):
        if self.voucher_type != "Sales Order":
            return

        from comfort.transactions import SalesOrder

        doc = get_doc(SalesOrder, self.voucher_no)
        if doc.docstatus != 2:
            doc.set_statuses()
            doc.save_without_validating()

    def on_cancel(self):
        cancel_gl_entries_for(self.doctype, self.name)
        self.set_status_in_sales_order()
