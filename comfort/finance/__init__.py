from __future__ import annotations

from typing import Any, Iterable, Literal, overload

import frappe
from comfort import OrderTypes
from frappe import _
from frappe.model.document import Document

from .doctype.accounts_settings.accounts_settings import AccountsSettings


@overload
def get_account(field_names: str) -> str:
    ...


@overload
def get_account(field_names: Iterable[str]) -> list[str]:
    ...


def get_account(field_names: str | Iterable[str]):
    return_str = False
    if isinstance(field_names, str):
        field_names = [field_names]
        return_str = True

    settings_name = "Accounts Settings"
    settings: AccountsSettings = frappe.get_cached_doc(settings_name, settings_name)
    accounts: list[str] = []
    for d in field_names:
        account = f"default_{d}_account"
        if hasattr(settings, account):
            accounts.append(getattr(settings, account))
        else:
            err_msg: str = _('Account Settings has no field "{}"').format(account)
            raise ValueError(err_msg)

    return accounts[0] if return_str else accounts


def get_received_amount(doc: Document) -> int:
    """Get balance from all GL Entries associated with given Transaction and default Cash or Bank accounts"""
    accounts = get_account(("cash", "bank"))

    payments: list[Any] = frappe.get_all(
        "Payment", {"voucher_type": doc.doctype, "voucher_no": doc.name}
    )
    payment_names = (p.name for p in payments)
    balances: list[Any] = frappe.get_all(
        "GL Entry",
        fields="SUM(debit - credit) as balance",
        filters={
            "account": ("in", accounts),
            "voucher_type": "Payment",
            "voucher_no": ("in", payment_names),
            "docstatus": ("!=", 2),
        },
    )
    return sum(b.balance or 0 for b in balances)


def create_gl_entry(
    doctype: Literal["Payment", "Receipt"],
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
    gl_entries: list[Any] = frappe.get_all(
        "GL Entry",
        {"voucher_type": doctype, "voucher_no": name, "docstatus": ("!=", 2)},
    )
    for entry in gl_entries:
        doc: Document = frappe.get_doc("GL Entry", entry.name)
        doc.cancel()


def create_payment(doctype: OrderTypes, name: str, amount: int, paid_with_cash: bool):
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
