from __future__ import annotations

from typing import Any, TypeVar

import frappe
from frappe.model.document import Document
from frappe.utils.data import cint

from .doctype.accounts_settings.accounts_settings import AccountsSettings
from .doctype.gl_entry.gl_entry import GLEntry


def make_gl_entry(self: Document, account: str, dr: int, cr: int):
    customer = None
    if hasattr(self, "customer") and self.get("customer"):
        customer = self.customer

    frappe.get_doc(
        {
            "doctype": "GL Entry",
            "account": account,
            "debit_amount": dr,
            "credit_amount": cr,
            "voucher_type": self.doctype,
            "voucher_no": self.name,
            "customer": customer,
        }
    ).submit()


def make_reverse_gl_entry(
    voucher_type: str | None = None, voucher_no: str | None = None
):
    gl_entries: list[Any] = frappe.get_all(
        "GL Entry",
        filters={"voucher_type": voucher_type, "voucher_no": voucher_no},
        fields=["*"],
    )

    if gl_entries:
        cancel_gl_entry(gl_entries[0].voucher_type, gl_entries[0].voucher_no)

        for entry in gl_entries:
            debit = entry.debit_amount
            credit = entry.credit_amount
            entry.name = None
            entry.debit_amount = credit
            entry.credit_amount = debit
            entry.is_cancelled = 1
            entry.remarks = "Cancelled GL Entry (" + entry.voucher_no + ")"

            if entry.debit_amount or entry.credit_amount:
                make_cancelled_gl_entry(entry)


def make_cancelled_gl_entry(entry: GLEntry):
    gl_entry = frappe.new_doc("GL Entry")
    gl_entry.update(entry)
    gl_entry.submit()


def cancel_gl_entry(voucher_type: str, voucher_no: str):
    frappe.db.sql(
        """
        UPDATE `tabGL Entry`
        SET is_cancelled=1
        WHERE voucher_type=%s
        AND voucher_no=%s AND is_cancelled=0
        """,
        (voucher_type, voucher_no),
    )


T = TypeVar("T", str, list[str])


def get_account(field_names: T) -> T:
    return_str = False
    if isinstance(field_names, str):
        field_names = [field_names]
        return_str = True
    settings_name = "Accounts Settings"
    settings: AccountsSettings = frappe.get_cached_doc(settings_name, settings_name)
    accounts = []
    for d in field_names:
        account = f"default_{d}_account"
        if hasattr(settings, account):
            accounts.append(getattr(settings, account))

    return accounts[0] if return_str else accounts


def get_paid_amount(dt: str, dn: str) -> int:
    accounts = get_account(["cash", "bank"])
    balance = frappe.get_list(
        "GL Entry",
        "SUM(debit_amount - credit_amount) as balance",
        {
            "is_cancelled": 0,
            "account": ["in", accounts],
            "voucher_type": dt,
            "voucher_no": dn,
        },
    )
    if balance and balance[0]:
        balance = cint(balance[0].balance)
        return balance if dt != "Purchase Order" else -balance
    else:
        return 0
