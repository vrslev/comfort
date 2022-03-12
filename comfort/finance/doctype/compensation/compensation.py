from typing import Any, Literal

from comfort.finance.utils import cancel_gl_entries_for, create_gl_entry, get_account
from comfort.utils import TypedDocument, ValidationError, _, get_value


class Compensation(TypedDocument):
    doctype: Literal["Compensation"]
    voucher_type: Literal["Purchase Order", "Sales Order"]
    status: Literal["Draft", "Received", "Cancelled"]
    voucher_no: str
    amount: int
    paid_with_cash: bool

    def validate_docstatus(self):
        if int(get_value(self.voucher_type, self.voucher_no, "docstatus")) != 1:
            raise ValidationError(_("Can only add compensation for submitted document"))

    def set_status(self) -> None:
        d: dict[int, Any] = {0: "Draft", 1: "Received", 2: "Cancelled"}
        self.status = d[self.docstatus]

    def validate(self) -> None:
        self.validate_docstatus()
        self.set_status()

    def before_submit(self) -> None:
        bank_or_cash = get_account("cash" if self.paid_with_cash else "bank")
        accounts = {
            "Purchase Order": (get_account("purchase_compensations"), bank_or_cash),
            "Sales Order": (bank_or_cash, get_account("sales_compensations")),
        }[self.voucher_type]

        create_gl_entry(self.doctype, self.name, accounts[0], 0, self.amount)
        create_gl_entry(self.doctype, self.name, accounts[1], self.amount, 0)

    def on_cancel(self) -> None:  # pragma: no cover
        cancel_gl_entries_for(self.doctype, self.name)
