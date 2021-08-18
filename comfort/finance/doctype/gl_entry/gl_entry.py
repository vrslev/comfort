import frappe
from frappe.model.document import Document


class GLEntry(Document):
    account: str
    debit: int
    credit: int
    voucher_type: str
    voucher_no: str

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
        return doc

    @staticmethod
    def cancel_for(doctype: str, name: str):
        gl_entries: list[GLEntry] = frappe.get_all(
            "GL Entry",
            {"voucher_type": doctype, "voucher_no": name, "docstatus": ("!=", 2)},
        )
        for entry in gl_entries:
            frappe.get_doc("GL Entry", entry.name).cancel()
