import pytest

import frappe
from comfort import doc_exists, get_all, get_doc, get_value
from comfort.finance import create_gl_entry
from comfort.finance.doctype.account.account import Account, add_node, get_children
from comfort.finance.doctype.gl_entry.gl_entry import GLEntry


@pytest.mark.usefixtures("accounts")
def test_get_children_root():
    assert get_children("Account") == get_all(
        Account,
        field=("name as value", "is_group as expandable", "parent_account"),
        filter={"parent_account": ""},
        order_by="name",
    )


@pytest.mark.usefixtures("accounts")
def test_get_children_not_root_all_entries_present():
    res = get_children("Account", "Income")
    for account in res:
        if "balance" in account:
            del account["balance"]

    assert res == get_all(
        Account,
        field=("name as value", "is_group as expandable", "parent_account"),
        filter={"parent_account": "Income"},
        order_by="name",
    )


@pytest.mark.usefixtures("accounts")
def test_get_children_not_root_balance():
    create_gl_entry(None, None, "Sales", 0, 300)  # type: ignore
    create_gl_entry(None, None, "Sales", 0, 500)  # type: ignore
    doc = get_doc(GLEntry, get_value("GL Entry", {"account": "Sales"}))
    doc.docstatus = 2
    doc.db_update()

    res = get_children("Account", "Income")
    assert {
        "value": "Sales",
        "expandable": 0,
        "parent_account": "Income",
        "balance": -300,
    } in res
    assert {
        "value": "Sales",
        "expandable": 0,
        "parent_account": "Income",
        "balance": -500,
    } not in res


def test_add_node():
    doctype, name, is_group = "Account", "Account Name", "0"
    frappe.form_dict = {
        "doctype": doctype,
        "account_name": name,
        "is_group": is_group,
        "parent": "Account",
        "is_root": "true",
        "cmd": "comfort.finance.doctype.account.account.add_node",
    }
    add_node()
    assert (
        doc_exists(
            {"doctype": doctype, "account_name": name, "is_group": bool(is_group)}
        )
        is not None
    )
