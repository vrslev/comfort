from __future__ import annotations

from typing import Literal

from comfort.utils import TypedDocument, ValidationError, _, get_value


class GLEntry(TypedDocument):
    voucher_type: Literal[
        "Payment",
        "Receipt",
        "Sales Return",
        "Purchase Return",
        "Compensation",
        "Money Transfer",
    ]
    voucher_no: str
    account: str
    debit: int
    credit: int

    def validate(self):
        if get_value("Account", self.account, "is_group"):
            raise ValidationError(_("Can't add GL Entry for group account"))
