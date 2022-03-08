from __future__ import annotations

from typing import Any

from comfort.finance import Account, FinanceSettings
from comfort.utils import get_all, get_doc, new_doc
from frappe.utils.nestedset import rebuild_tree

ACCOUNTS: dict[str, dict[str, Any]] = {
    "Assets": {
        "Bank": {},
        "Cash": {},
        "Inventory": {},
        "Prepaid Inventory": {},
    },
    "Liabilities": {
        "Prepaid Sales": {},
    },
    "Expense": {
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
    "purchase_delivery_account": "Purchase Delivery",
    "prepaid_sales_account": "Prepaid Sales",
    "sales_account": "Sales",
    "delivery_account": "Delivery",
    "installation_account": "Installation",
    "sales_compensations_account": "Sales Compensations",
    "purchase_compensations_account": "Purchase Compensations",
}


def _create_accounts_from_schema():
    def execute(parent: str | None, children: dict[str, Any]):
        for child, children_of_child in children.items():
            doc = new_doc(Account)
            doc.account_name = child
            doc.parent_account = parent
            doc.is_group = bool(children_of_child)
            doc.insert()
            execute(child, children_of_child)

    execute(None, ACCOUNTS)
    rebuild_tree("Account", "parent_account")


def _set_default_accounts():
    doc = get_doc(FinanceSettings)
    doc.update(DEFAULT_ACCOUNT_SETTINGS)
    doc.save()


def initialize_accounts():
    if not get_all(Account, limit=1):
        _create_accounts_from_schema()
    _set_default_accounts()
