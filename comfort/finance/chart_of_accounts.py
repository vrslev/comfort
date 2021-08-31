from __future__ import annotations

from typing import Any

import frappe
from comfort.finance.doctype.finance_settings.finance_settings import FinanceSettings
from frappe import _
from frappe.utils.nestedset import rebuild_tree

ACCOUNTS: dict[str, dict[str, Any]] = {
    "Assets": {
        "Bank": {},
        "Cash": {},
        "Inventory": {},
        "Prepaid Inventory": {},
    },
    "Expense": {
        "Cost of Goods Sold": {},
        "Purchase Delivery": {},
        "Sales Compensations": {},
    },
    "Income": {
        "Purchase Compensations": {},
        "Sales": {},
        "Service": {"Delivery": {}, "Installation": {}},
    },
}

DEFAULT_ACCOUNT_SETTINGS = {
    "bank_account": "Bank",
    "cash_account": "Cash",
    "prepaid_inventory_account": "Prepaid Inventory",
    "inventory_account": "Inventory",
    "cost_of_goods_sold_account": "Cost of Goods Sold",
    "purchase_delivery_account": "Purchase Delivery",
    "sales_account": "Sales",
    "delivery_account": "Delivery",
    "installation_account": "Installation",
    "sales_compensations_account": "Sales Compensations",
    "purchase_compensations_account": "Purchase Compensations",
}


def _create_accounts_from_schema():
    def execute(parent: str | None, children: dict[str, Any]):
        for child, children_of_child in children.items():
            frappe.get_doc(
                {
                    "doctype": "Account",
                    "account_name": _(child),
                    "parent_account": _(parent),
                    "is_group": bool(children_of_child),
                }
            ).insert()
            execute(child, children_of_child)

    execute(None, ACCOUNTS)
    rebuild_tree("Account", "parent_account")


def _set_default_accounts():
    doc: FinanceSettings = frappe.get_single("Finance Settings")
    doc.update(DEFAULT_ACCOUNT_SETTINGS)
    doc.save()


def initialize_accounts():
    if not frappe.get_all("Account", limit_page_length=1):
        _create_accounts_from_schema()
    _set_default_accounts()
