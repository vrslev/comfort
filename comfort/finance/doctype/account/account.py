from __future__ import annotations

from typing import Any

import frappe
from comfort.finance.doctype.gl_entry.gl_entry import GLEntry
from comfort.utils import get_all, get_doc
from frappe.desk.treeview import make_tree_args
from frappe.utils.nestedset import NestedSet


class Account(NestedSet):
    name: str | None
    account_name: str
    is_group: bool
    parent_account: str | None
    indent: int


@frappe.whitelist()
def get_children(doctype: str, parent: str = "", is_root: bool = False):
    accounts: list[Any] = frappe.get_all(
        doctype,
        fields=("name as value", "is_group as expandable", "parent_account"),
        filters={"parent_account": parent},
        order_by="name",
    )
    for account in accounts:
        if account.expandable:
            continue

        v: list[Any] = get_all(
            GLEntry,
            field="SUM(debit) - SUM(credit) as balance",
            filter={"account": account.value, "docstatus": ("!=", 2)},
        )
        account.balance = v[0].balance or 0
    return accounts


@frappe.whitelist()
def add_node() -> None:
    args: Any = make_tree_args(**frappe.form_dict)  # type: ignore
    if args.is_root:
        args.parent_account = None
    get_doc(Account, args).insert()
