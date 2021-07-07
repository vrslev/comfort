import frappe
from frappe import _
from frappe.utils.nestedset import rebuild_tree
from six import iteritems


def create_charts():
    chart = {
        _("Assets"): {
            _("Bank"): {"account_type": "Bank"},
            _("Cash"): {"account_type": "Cash"},
            _("Inventory"): {"account_type": "Stock"},
            _("Prepaid Inventory"): {"account_type": "Receivable"},
            "root_type": "Asset",
        },
        _("Expenses"): {
            _("Cost of Goods Sold"): {"account_type": "Cost of Goods Sold"},
            _("Purchase Delivery"): {"account_type": ""},
            _("Sales Compensations"): {"account_type": ""},
            "root_type": "Expense",
        },
        _("Income"): {
            _("Purchase Compensations"): {"account_type": ""},
            _("Sales"): {"account_type": "Income Account"},
            _("Service"): {
                _("Delivery"): {"account_type": ""},
                _("Installation"): {"account_type": ""},
            },
            "root_type": "Income",
        },
        _("Liabilities"): {
            _("Prepaid Orders"): {"account_type": "Payable"},
            "root_type": "Liability",
        },
    }

    def _import_accounts(children, parent, root_type, root_account=False):
        for account_name, child in iteritems(children):
            if root_account:
                root_type = child.get("root_type")

            if account_name not in ["account_type", "root_type", "is_group"]:
                is_group = identify_is_group(child)

                account = frappe.get_doc(
                    {
                        "doctype": "Account",
                        "account_name": account_name,
                        "account_type": child.get("account_type"),
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


def identify_is_group(child):
    if child.get("is_group"):
        is_group = child.get("is_group")
    elif len(set(child.keys()) - set(["account_type", "root_type", "is_group"])):
        is_group = 1
    else:
        is_group = 0

    return is_group
