from __future__ import annotations

from typing import Literal

from comfort import TypedDocument


class GLEntry(TypedDocument):
    voucher_type: Literal[
        "Payment", "Receipt", "Sales Return", "Purchase Return", "Compensation"
    ]
    voucher_no: str
    account: str
    debit: int
    credit: int
