from __future__ import annotations

from typing import Any

import frappe
from frappe import _
from frappe.utils.nestedset import rebuild_tree


def create_charts():
    chart: dict[str, Any] = {
        _("Assets"): {
            _("Bank"): {},
            _("Cash"): {},
            _("Inventory"): {},
            _("Prepaid Inventory"): {},
            "root_type": "Asset",
        },
        _("Expenses"): {
            _("Cost of Goods Sold"): {},
            _("Purchase Delivery"): {},
            _("Sales Compensations"): {},
            "root_type": "Expense",
        },
        _("Income"): {
            _("Purchase Compensations"): {},
            _("Sales"): {},
            _("Service"): {_("Delivery"): {}, _("Installation"): {}},
            "root_type": "Income",
        },
        _("Liabilities"): {"root_type": "Liability", "is_group": 1},
    }

    def _import_accounts(
        children: dict[Any, Any],
        parent: str,
        root_type: str,
        root_account: bool = False,
    ):
        for account_name, child in children.items():
            if root_account:
                root_type = child.get("root_type")

            if account_name not in ["root_type", "is_group"]:
                is_group = identify_is_group(child)

                account = frappe.get_doc(
                    {
                        "doctype": "Account",
                        "account_name": account_name,
                        "parent_account": parent,
                        "is_group": is_group,
                        "root_type": root_type,
                    }
                )

                if root_account:
                    account.flags.ignore_mandatory = True

                account.flags.ignore_permissions = True

                account.insert()

                _import_accounts(child, account.name, root_type)

    # Rebuild NestedSet HSM tree for Account Doctype
    # after all accounts are already inserted.
    frappe.local.flags.ignore_on_update = True
    _import_accounts(chart, None, None, root_account=True)
    rebuild_tree("Account", "parent_account")
    frappe.local.flags.ignore_on_update = False


def identify_is_group(child: dict[Any, Any]):
    if child.get("is_group"):
        is_group = child.get("is_group")
    elif len(set(child.keys()) - {"root_type", "is_group"}):
        is_group = 1
    else:
        is_group = 0

    return is_group
