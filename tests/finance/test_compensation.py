from __future__ import annotations

import pytest

import frappe
from comfort import get_all, new_doc
from comfort.finance import get_account
from comfort.finance.doctype.compensation.compensation import Compensation
from comfort.finance.doctype.gl_entry.gl_entry import GLEntry
from comfort.transactions.doctype.purchase_order.purchase_order import PurchaseOrder
from comfort.transactions.doctype.sales_order.sales_order import SalesOrder


@pytest.mark.parametrize("docstatus", (0, 2))
def test_compensation_validate_raises(docstatus: int):
    ref_doc = new_doc(SalesOrder)
    ref_doc.docstatus = docstatus
    ref_doc.db_insert()

    doc = new_doc(Compensation)
    doc.voucher_type = ref_doc.doctype
    doc.voucher_no = ref_doc.name

    with pytest.raises(
        frappe.exceptions.ValidationError,
        match="Can only add compensation for submitted document",
    ):
        doc.validate()


def test_compensation_validate_passes():
    ref_doc = new_doc(SalesOrder)
    ref_doc.docstatus = 1
    ref_doc.db_insert()

    doc = new_doc(Compensation)
    doc.voucher_type = ref_doc.doctype
    doc.voucher_no = ref_doc.name
    doc.validate()


@pytest.mark.parametrize(
    ("cls_", "paid_with_cash", "exp_accounts_to_amounts"),
    (
        (SalesOrder, True, {"cash": (0, 100), "sales_compensations": (100, 0)}),
        (SalesOrder, False, {"bank": (0, 100), "sales_compensations": (100, 0)}),
        (PurchaseOrder, True, {"purchase_compensations": (0, 100), "cash": (100, 0)}),
        (PurchaseOrder, False, {"purchase_compensations": (0, 100), "bank": (100, 0)}),
    ),
)
def test_compensation_before_submit(
    cls_: type[SalesOrder | PurchaseOrder],
    paid_with_cash: bool,
    exp_accounts_to_amounts: dict[str, tuple[int, int]],
):
    ref_doc = new_doc(cls_)
    ref_doc.db_insert()

    doc = new_doc(Compensation)
    doc.voucher_type = ref_doc.doctype
    doc.voucher_no = ref_doc.name
    doc.amount = 100
    doc.paid_with_cash = paid_with_cash
    doc.before_submit()

    exp_accounts_to_amounts = {
        get_account(field): amounts
        for field, amounts in exp_accounts_to_amounts.items()
    }
    for entry in get_all(
        GLEntry,
        filters={"voucher_type": doc.doctype, "voucher_no": doc.name},
        fields=("account", "debit", "credit"),
    ):
        assert entry.account in exp_accounts_to_amounts.keys()
        assert (entry.debit, entry.credit) == exp_accounts_to_amounts[entry.account]
