import frappe
from comfort.finance.doctype.gl_entry.gl_entry import GLEntry
from comfort.finance.doctype.payment.payment import Payment


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
