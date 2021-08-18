from typing import Literal

import frappe
from frappe.model.document import Document

_TransactionType = Literal["Invoice", "Delivery"]


class GLEntry(Document):
    type: _TransactionType
    is_cancelled: bool
    account: str
    debit: int
    credit: int
    voucher_type: str
    voucher_no: str
    remarks: str

    @staticmethod
    def new(
        doc: Document, type_: _TransactionType, account: str, debit: int, credit: int
    ):
        frappe.get_doc(
            {
                "doctype": "GL Entry",
                "type": type_,
                "account": account,
                "debit": debit,
                "credit": credit,
                "voucher_type": doc.doctype,
                "voucher_no": doc.name,
            }
        ).submit()

    @staticmethod
    def cancel_entries_for(doc: Document):
        gl_entries: list[GLEntry] = frappe.get_all(
            "GL Entry",
            filters={
                "voucher_type": doc.doctype,
                "voucher_no": doc.name,
                "is_cancelled": 0,
            },
            fields=["name"],
        )
        for entry_ in gl_entries:
            frappe.get_doc("GL Entry", entry_.name).cancel()
