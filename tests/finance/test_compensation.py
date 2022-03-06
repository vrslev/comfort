from __future__ import annotations

import pytest

import frappe
from comfort import get_all, new_doc
from comfort.finance import Compensation, GLEntry
from comfort.finance.utils import get_account
from comfort.transactions import PurchaseOrder, SalesOrder


@pytest.mark.parametrize("docstatus", (0, 2))
def test_compensation_validate_docstatus_raises(docstatus: int):
    ref_doc = new_doc(SalesOrder)
    ref_doc.docstatus = docstatus
    ref_doc.db_insert()

    doc = new_doc(Compensation)
    doc.voucher_type = ref_doc.doctype
    doc.voucher_no = ref_doc.name

    with pytest.raises(frappe.exceptions.ValidationError, match="submitted document"):
        doc.validate()


def test_compensation_validate_docstatus_passes():
    ref_doc = new_doc(SalesOrder)
    ref_doc.docstatus = 1
    ref_doc.db_insert()

    doc = new_doc(Compensation)
    doc.voucher_type = ref_doc.doctype
    doc.voucher_no = ref_doc.name
    doc.validate()


@pytest.mark.parametrize(
    ("cls_", "cash", "accounts_to_amounts"),
    (
        (SalesOrder, True, {"cash": (0, 100), "sales_compensations": (100, 0)}),
        (SalesOrder, False, {"bank": (0, 100), "sales_compensations": (100, 0)}),
        (PurchaseOrder, True, {"purchase_compensations": (0, 100), "cash": (100, 0)}),
        (PurchaseOrder, False, {"purchase_compensations": (0, 100), "bank": (100, 0)}),
    ),
)
def test_compensation_before_submit(
    cls_: type[SalesOrder | PurchaseOrder],
    cash: bool,
    accounts_to_amounts: dict[str, tuple[int, int]],
):
    ref_doc = new_doc(cls_)
    ref_doc.db_insert()

    doc = new_doc(Compensation)
    doc.voucher_type = ref_doc.doctype
    doc.voucher_no = ref_doc.name
    doc.amount = 100
    doc.paid_with_cash = cash
    doc.before_submit()

    accounts_to_amounts = {
        get_account(field): amounts for field, amounts in accounts_to_amounts.items()
    }

    for entry in get_all(
        GLEntry,
        filter={"voucher_type": doc.doctype, "voucher_no": doc.name},
        field=("account", "debit", "credit"),
    ):
        assert entry.account in accounts_to_amounts.keys()
        assert (entry.debit, entry.credit) == accounts_to_amounts[entry.account]
