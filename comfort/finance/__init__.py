from __future__ import annotations

from typing import Any, Iterable, overload

import frappe
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
    entries: list[Any] = frappe.get_all(
        "GL Entry",
        fields="SUM(debit - credit) as balance",
        filters={
            "account": ["in", accounts],
            "voucher_type": doc.doctype,
            "voucher_no": doc.name,
            "is_cancelled": 0,
        },
        limit_page_length=1,
    )
    return sum(entry.balance or 0 for entry in entries)
