"""
v0.25.0

Currently:

- "Sales" account contains cost of goods that not sold yet and margin
- "Cost of Goods Sold" contains cost of goods already sold

To do:

- Sales Return

  - Transfer all GL Entries with "Sales" account to Prepaid Sales

- Payment Sales
  - Remove all GL Entries and create new ones

<!-- - Payment Purchase -->

- Receipt Sales
  <!-- - Remove GL Entries with "Cost Of Goods Sold" account -->
  - Remove all GL Entries and create new ones

<!-- - Receipt Purchase -->
"""

from copy import deepcopy

from comfort import get_all, get_doc, new_doc
from comfort.finance.doctype.account.account import Account
from comfort.finance.doctype.finance_settings.finance_settings import FinanceSettings
from comfort.finance.doctype.gl_entry.gl_entry import GLEntry
from comfort.finance.doctype.payment.payment import Payment
from comfort.stock.doctype.receipt.receipt import Receipt
from comfort.transactions.doctype.sales_order.sales_order import SalesOrder


def create_account():
    parent = new_doc(Account)
    parent.account_name = "Liabilities"
    parent.is_group = True
    parent.save()

    doc = new_doc(Account)
    doc.account_name = "Prepaid Sales"
    doc.parent_account = parent.name
    doc.save()


def migrate() -> None:
    from frappe.migrate import migrate

    migrate(verbose=True)


def set_prepaid_sales_default_account():
    doc = get_doc(FinanceSettings)
    doc.prepaid_sales_account = "Prepaid Sales"  # type: ignore
    doc.save()


def sales_return():
    for entry in get_all(
        GLEntry, filter={"voucher_type": "Sales Return", "account": "Sales"}
    ):
        doc = get_doc(GLEntry, entry.name)
        doc.account = "Prepaid Sales"
        doc.db_update()


def payment_sales():
    payments = get_all(Payment, filter={"voucher_type": "Sales Order", "docstatus": 1})
    for payment in payments:
        entries = get_all(
            GLEntry, filter={"voucher_type": "Payment", "voucher_no": payment.name}
        )
        for entry in entries:
            entry_doc = get_doc(GLEntry, entry.name)
            if entry_doc.docstatus == 1:
                entry_doc.cancel()
            entry_doc.delete()

        doc = get_doc(Payment, payment.name)
        doc.create_sales_gl_entries()


def receipt_sales():
    receipts = get_all(Receipt, filter={"voucher_type": "Sales Order", "docstatus": 1})
    for receipt in receipts:
        entries = get_all(
            GLEntry, filter={"voucher_type": "Receipt", "voucher_no": receipt.name}
        )
        for entry in entries:
            entry_doc = get_doc(GLEntry, entry.name)
            if entry_doc.docstatus == 1:
                entry_doc.cancel()
            entry_doc.delete()

        doc = get_doc(Receipt, receipt.name)
        doc.create_sales_gl_entries()


def remove_costs_of_goods_sold():
    import frappe

    frappe.delete_doc("Account", "Cost of Goods Sold")


def check_if_statuses_changed():
    for name in get_all(SalesOrder, pluck="name", filter={"docstatus": 1}):
        doc = get_doc(SalesOrder, name)
        values_before = deepcopy(
            (
                doc.paid_amount,
                doc.status,
                doc.delivery_status,
                doc.payment_status,
            )
        )
        doc.set_statuses()
        values_after = (
            doc.paid_amount,
            doc.status,
            doc.delivery_status,
            doc.payment_status,
        )

        for idx, value in enumerate(values_before):
            if value != values_after[idx]:
                raise Exception(value, values_after[idx], doc)

        if values_before != values_after:
            raise Exception(values_before, values_after)


def main():
    create_account()
    migrate()
    set_prepaid_sales_default_account()
    sales_return()
    payment_sales()
    receipt_sales()
    remove_costs_of_goods_sold()
    check_if_statuses_changed()
