import re

import pytest

import frappe
from comfort.finance import GLEntry, Payment
from comfort.finance.chart_of_accounts import DEFAULT_ACCOUNT_SETTINGS
from comfort.finance.utils import (
    cancel_gl_entries_for,
    create_gl_entry,
    create_payment,
    get_account,
)
from comfort.transactions import SalesOrder
from comfort.utils import get_all, get_value


@pytest.mark.usefixtures("accounts")
def test_get_account():
    for field_name, account in DEFAULT_ACCOUNT_SETTINGS.items():
        shorten_field_name = re.findall(r"(.*)_account", field_name)[0]
        assert get_account(shorten_field_name) == account


@pytest.mark.usefixtures("accounts")
def test_get_account_raises_on_wrong_name():
    account_name = "toys"
    with pytest.raises(
        frappe.ValidationError,
        match=f'Finance Settings has no field "{account_name}_account"',
    ):
        return get_account(account_name)


def test_create_gl_entry(payment_sales: Payment):
    payment_sales.db_insert()
    account, debit, credit = get_account("cash"), 300, 0
    create_gl_entry(payment_sales.doctype, payment_sales.name, account, debit, credit)
    entries = get_all(
        GLEntry,
        field=("docstatus", "account", "debit", "credit"),
        filter={
            "voucher_type": payment_sales.doctype,
            "voucher_no": payment_sales.name,
        },
    )

    assert entries[0].docstatus == 1
    assert entries[0].account == account
    assert entries[0].debit == debit
    assert entries[0].credit == credit


def test_cancel_gl_entries_for(payment_sales: Payment):
    payment_sales.db_insert()
    create_gl_entry(
        payment_sales.doctype, payment_sales.name, get_account("cash"), 300, 0
    )

    cancel_gl_entries_for(payment_sales.doctype, payment_sales.name)
    docstatus: int = get_value(
        "GL Entry",
        fieldname="docstatus",
        filters={
            "voucher_type": payment_sales.doctype,
            "voucher_no": payment_sales.name,
        },
    )
    assert docstatus == 2


def test_create_payment(sales_order: SalesOrder):
    sales_order.db_insert()
    amount, paid_with_cash = 300, True

    create_payment(
        sales_order.doctype, sales_order.name, amount, paid_with_cash=paid_with_cash
    )

    payments = get_all(
        Payment,
        field=("amount", "paid_with_cash"),
        filter={
            "voucher_type": sales_order.doctype,
            "voucher_no": sales_order.name,
        },
    )

    assert payments[0].amount == amount
    assert payments[0].paid_with_cash == paid_with_cash
