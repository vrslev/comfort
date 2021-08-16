from typing import TYPE_CHECKING

import pytest

import frappe
from comfort.finance import get_account
from comfort.finance.doctype.gl_entry.gl_entry import GLEntry
from comfort.transactions.doctype.sales_order.sales_order import SalesOrder

if not TYPE_CHECKING:
    from tests.entities.test_customer import customer
    from tests.entities.test_item import child_items, item
    from tests.transactions.test_sales_order import sales_order


@pytest.fixture
def gl_entry() -> GLEntry:
    return frappe.get_doc(
        {
            "name": "GLE-2021-00001",
            "owner": "Administrator",
            "type": "Invoice",
            "is_cancelled": 0,
            "account": "Delivery",
            "debit": 0,
            "credit": 300,
            "voucher_type": "Sales Order",
            "voucher_no": "SO-2021-0001",
            "doctype": "GL Entry",
        }
    )


def test_gl_entry_new(sales_order: SalesOrder):
    type_, account = "Invoice", get_account("delivery")
    debit, credit = 0, 300
    sales_order.db_insert()
    GLEntry.new(sales_order, type_, account, debit, credit)
    entry: GLEntry = frappe.get_all(
        "GL Entry",
        filters={"voucher_type": sales_order.doctype, "voucher_no": sales_order.name},
        fields=["type", "account", "debit", "credit", "is_cancelled", "docstatus"],
        limit_page_length=1,
    )[0]

    assert entry.type == type_
    assert entry.account == account
    assert entry.debit == debit
    assert entry.credit == credit
    assert entry.is_cancelled == 0
    assert entry.docstatus == 1


def test_make_reverse_entries_new_entry(sales_order: SalesOrder, gl_entry: GLEntry):
    sales_order.db_insert()
    gl_entry.insert()
    GLEntry.make_reverse_entries(sales_order)

    gl_entries: list[GLEntry] = frappe.get_all(
        "GL Entry",
        filters={"voucher_type": sales_order.doctype, "voucher_no": sales_order.name},
        fields=["remarks", "debit", "credit"],
    )
    remarks: list[str] = []
    balance = 0
    for entry in gl_entries:
        remarks.append(entry.remarks)
        balance += entry.debit - entry.credit

    assert balance == 0
    assert f"On cancellation of {gl_entry.voucher_no}" in remarks


def test_make_reverse_entries_old_entry_is_cancelled(
    sales_order: SalesOrder, gl_entry: GLEntry
):
    sales_order.db_insert()
    gl_entry.insert()
    GLEntry.make_reverse_entries(sales_order)

    assert gl_entry.get_db_value("is_cancelled") == 1
