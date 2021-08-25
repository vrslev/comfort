from __future__ import annotations

from typing import Any

import frappe
from comfort.finance.doctype.accounts_settings.accounts_settings import AccountsSettings
from frappe import _
from frappe.utils.nestedset import rebuild_tree

ACCOUNTS: dict[str, dict[str, Any]] = {
    "Assets": {
        "Bank": {},
        "Cash": {},
        "Inventory": {},
        "Prepaid Inventory": {},
    },
    "Expenses": {
        "Cost of Goods Sold": {},
        "Purchase Delivery": {},
        "Sales Compensations": {},
    },
    "Income": {
        "Purchase Compensations": {},
        "Sales": {},
        "Service": {"Delivery": {}, "Installation": {}},
    },
    "Liabilities": {},
}

DEFAULT_ACCOUNT_SETTINGS = {
    "default_bank_account": "Bank",
    "default_cash_account": "Cash",
    "default_prepaid_inventory_account": "Prepaid Inventory",
    "default_inventory_account": "Inventory",
    "default_cost_of_goods_sold_account": "Cost of Goods Sold",
    "default_purchase_delivery_account": "Purchase Delivery",
    "default_sales_account": "Sales",
    "default_delivery_account": "Delivery",
    "default_installation_account": "Installation",
    "default_sales_compensations_account": "Sales Compensations",
    "default_purchase_compensations_account": "Purchase Compensations",
}


def _create_accounts_from_schema():  # TODO: All account are groups
    def execute(parent: str | None, children: dict[str, Any]):
        for child, children_of_child in children.items():
            frappe.get_doc(
                {
                    "doctype": "Account",
                    "account_name": _(child),
                    "parent_account": _(parent),
                    "is_group": 1,
                }
            ).insert()
            execute(child, children_of_child)

    execute(None, ACCOUNTS)
    rebuild_tree("Account", "parent_account")


def _set_default_accounts():
    doc: AccountsSettings = frappe.get_single("Accounts Settings")
    doc.update(DEFAULT_ACCOUNT_SETTINGS)
    doc.save()


def initialize_accounts():
    if not frappe.get_all("Account", limit_page_length=1):
        _create_accounts_from_schema()
    _set_default_accounts()
