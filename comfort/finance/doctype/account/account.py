from __future__ import annotations

from typing import Any

import frappe
from frappe.desk.treeview import make_tree_args
from frappe.utils.nestedset import NestedSet


class Account(NestedSet):
    account_name: str
    is_group: bool
    parent_account: str


@frappe.whitelist()
def get_children(doctype: str, parent: str = "", is_root: bool = False):
    accounts: list[Any] = frappe.get_all(
        doctype,
        fields=("name as value", "is_group as expandable", "parent_account"),
        filters={"parent_account": parent},
        order_by="name",
    )
    for account in accounts:
        if not account.expandable:
            v: list[Any] = frappe.get_all(
                "GL Entry",
                fields="SUM(debit) - SUM(credit) as balance",
                filters={"account": account.value, "docstatus": ("!=", 2)},
            )
            account.balance = v[0].balance if v and v[0] and v[0].get("balance") else 0
    return accounts


@frappe.whitelist()
def add_node():
    args = make_tree_args(**frappe.form_dict)
    if args.is_root:
        args.parent_account = None
    doc: Account = frappe.get_doc(args)
    doc.insert()
