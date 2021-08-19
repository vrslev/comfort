from __future__ import annotations

from typing import Literal

import frappe
from frappe.model.document import Document


class GLEntry(Document):
    voucher_type: Literal["Payment", "Receipt"]
    voucher_no: str
    account: str
    debit: int
    credit: int

    @staticmethod
    def create_for(
        doctype: str, name: str, account: str, debit: int, credit: int
    ):  # pragma: no cover
        doc: GLEntry = frappe.get_doc(
            {
                "doctype": "GL Entry",
                "account": account,
                "debit": debit,
                "credit": credit,
                "voucher_type": doctype,
                "voucher_no": name,
            }
        )
        doc.insert()
        doc.submit()

    @staticmethod
    def cancel_for(doctype: str, name: str):
        gl_entries: list[GLEntry] = frappe.get_all(
            "GL Entry",
            {"voucher_type": doctype, "voucher_no": name, "docstatus": ("!=", 2)},
        )
        for entry in gl_entries:
            doc: GLEntry = frappe.get_doc("GL Entry", entry.name)
            doc.cancel()
