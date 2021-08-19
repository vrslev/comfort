from __future__ import annotations

from typing import Literal

from frappe.model.document import Document


class GLEntry(Document):
    voucher_type: Literal["Payment", "Receipt"]
    voucher_no: str
    account: str
    debit: int
    credit: int
