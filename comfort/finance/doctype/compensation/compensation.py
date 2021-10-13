from typing import Literal

from comfort import TypedDocument, ValidationError, _, get_value
from comfort.finance import cancel_gl_entries_for, create_gl_entry, get_account


class Compensation(TypedDocument):
    doctype: Literal["Compensation"]
    voucher_type: Literal["Purchase Order", "Sales Order"]
    voucher_no: str
    amount: int
    paid_with_cash: bool

    def validate(self):
        if int(get_value(self.voucher_type, self.voucher_no, "docstatus")) != 1:
            raise ValidationError(_("Can only add compensation for submitted document"))

    def before_submit(self):
        bank_or_cash = get_account("cash" if self.paid_with_cash else "bank")
        accounts = {
            "Purchase Order": (get_account("purchase_compensations"), bank_or_cash),
            "Sales Order": (bank_or_cash, get_account("sales_compensations")),
        }[self.voucher_type]

        create_gl_entry(self.doctype, self.name, accounts[0], 0, self.amount)
        create_gl_entry(self.doctype, self.name, accounts[1], self.amount, 0)

    def on_cancel(self):  # pragma: no cover
        cancel_gl_entries_for(self.doctype, self.name)
