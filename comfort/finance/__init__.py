from __future__ import annotations

from typing import TypeVar

import frappe
from frappe import _

from .doctype.accounts_settings.accounts_settings import AccountsSettings

T = TypeVar("T", str, list[str], tuple[str])


def get_account(field_names: T):
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


def get_paid_amount(dt: str, dn: str) -> int:
    accounts = get_account(["cash", "bank"])
    balance: list[object] = frappe.get_all(
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
        balance = int(balance[0].balance)  # type: ignore
        return balance if dt != "Purchase Order" else -balance
    else:
        return 0
