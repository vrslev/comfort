from __future__ import annotations

from typing import Literal

import frappe
from comfort import ValidationError
from comfort.transactions import OrderTypes
from frappe import _
from frappe.model.document import Document


def get_account(field_name: str) -> str:
    settings_docname = "Finance Settings"
    actual_field_name = f"{field_name}_account"
    account: str | None = frappe.get_cached_value(
        settings_docname, settings_docname, actual_field_name
    )
    if account is None:
        raise ValidationError(
            _('Finance Settings has no field "{}"').format(actual_field_name)
        )
    return account


def create_gl_entry(
    doctype: Literal["Payment", "Receipt", "Sales Return", "Purchase Return"],
    name: str,
    account: str,
    debit: int,
    credit: int,
):
    doc: Document = frappe.get_doc(
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


def cancel_gl_entries_for(doctype: str, name: str):
    gl_entries: list[Document] = frappe.get_all(
        "GL Entry",
        {"voucher_type": doctype, "voucher_no": name, "docstatus": ("!=", 2)},
    )
    for entry in gl_entries:
        doc: Document = frappe.get_doc("GL Entry", entry.name)
        doc.cancel()


def create_payment(
    doctype: OrderTypes, name: str, amount: int, paid_with_cash: bool
):  # TODO: For consistency, pass whole doc to capture real state of the doc
    doc: Document = frappe.get_doc(
        {
            "doctype": "Payment",
            "voucher_type": doctype,
            "voucher_no": name,
            "amount": amount,
            "paid_with_cash": paid_with_cash,
        }
    )
    doc.insert()
    doc.submit()
