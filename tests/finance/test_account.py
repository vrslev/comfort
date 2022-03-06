import pytest

import frappe
from comfort import doc_exists, get_doc, get_value
from comfort.finance import GLEntry
from comfort.finance.doctype.account.account import add_node, get_children
from comfort.finance.utils import create_gl_entry


@pytest.mark.usefixtures("accounts")
def test_get_children():
    create_gl_entry(None, None, "Sales", 0, 300)  # type: ignore
    create_gl_entry(None, None, "Sales", 0, 500)  # type: ignore

    doc = get_doc(GLEntry, get_value("GL Entry", {"account": "Sales"}))
    doc.docstatus = 2
    doc.db_update()

    result = get_children("Account", "Income")

    assert {
        "value": "Sales",
        "expandable": 0,
        "parent_account": "Income",
        "balance": -300,
    } in result

    assert {
        "value": "Sales",
        "expandable": 0,
        "parent_account": "Income",
        "balance": -500,
    } not in result


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
