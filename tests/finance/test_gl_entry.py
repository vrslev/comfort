from typing import TYPE_CHECKING

import pytest

import frappe
from comfort.finance.doctype.gl_entry.gl_entry import GLEntry
from comfort.finance.doctype.payment.payment import Payment

if not TYPE_CHECKING:
    from tests.entities.test_customer import customer
    from tests.entities.test_item import child_items, item
    from tests.finance.test_payment import payment_sales
    from tests.transactions.test_sales_order import sales_order


@pytest.fixture
def gl_entry(payment_sales: Payment) -> GLEntry:
    payment_sales.db_insert()
    return frappe.get_doc(
        {
            "name": "GLE-2021-00001",
            "owner": "Administrator",
            "account": "Delivery",
            "debit": 0,
            "credit": 300,
            "voucher_type": "Payment",
            "voucher_no": "ebd35a9cc9",
            "doctype": "GL Entry",
        }
    )


def test_cancel_for(payment_sales: Payment, gl_entry: GLEntry):
    gl_entry.insert()
    gl_entry.submit()

    GLEntry.cancel_for(payment_sales.doctype, payment_sales.name)

    gl_entries: list[GLEntry] = frappe.get_all(
        "GL Entry",
        filters={
            "voucher_type": gl_entry.voucher_type,
            "voucher_no": gl_entry.voucher_no,
        },
        fields=["docstatus", "debit", "credit"],
    )
    balance = 0
    for entry in gl_entries:
        assert entry.docstatus == 2
        balance += entry.debit - entry.credit

    assert balance == gl_entry.debit - gl_entry.credit
