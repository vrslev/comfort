from typing import Literal

import frappe
from frappe import _
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
    def make_reverse_entries(doc: Document):
        gl_entries: list[GLEntry] = frappe.get_all(
            "GL Entry",
            filters={
                "voucher_type": doc.doctype,
                "voucher_no": doc.name,
                "is_cancelled": 0,
            },
            fields=["*"],
        )

        for entry in gl_entries:
            frappe.db.set_value("GL Entry", entry.name, "is_cancelled", True)
            frappe.get_doc(
                {
                    "doctype": "GL Entry",
                    "type": entry.type,
                    "account": entry.account,
                    "debit": entry.credit,
                    "credit": entry.debit,
                    "voucher_type": entry.voucher_type,
                    "voucher_no": entry.voucher_no,
                    "is_cancelled": 1,
                    "remarks": f"{_('On cancellation of')} {entry.voucher_no}",
                }
            ).submit()
