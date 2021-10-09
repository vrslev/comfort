from __future__ import annotations

from typing import Literal

from comfort import ValidationError, _, get_all, get_cached_value, get_doc, new_doc
from comfort.finance.doctype.gl_entry.gl_entry import GLEntry
from comfort.transactions import OrderTypes


def get_account(field_name: str) -> str:
    settings_docname = "Finance Settings"
    actual_field_name = f"{field_name}_account"
    account: str | None = get_cached_value(
        settings_docname, settings_docname, actual_field_name
    )
    if account is None:
        raise ValidationError(
            _('Finance Settings has no field "{}"').format(actual_field_name)
        )
    return account


def create_gl_entry(
    doctype: Literal[
        "Payment", "Receipt", "Sales Return", "Purchase Return", "Compensation"
    ],
    name: str,
    account: str,
    debit: int,
    credit: int,
):
    doc = new_doc(GLEntry)
    doc.account = account
    doc.debit = debit
    doc.credit = credit
    doc.voucher_type = doctype
    doc.voucher_no = name
    doc.insert().submit()


def cancel_gl_entries_for(
    doctype: Literal[
        "Payment", "Receipt", "Sales Return", "Purchase Return", "Compensation"
    ],
    name: str,
):
    for entry in get_all(
        GLEntry,
        {"voucher_type": doctype, "voucher_no": name, "docstatus": ("!=", 2)},
    ):
        get_doc(GLEntry, entry.name).cancel()


def create_payment(
    doctype: OrderTypes, name: str, amount: int, paid_with_cash: bool
):  # TODO: For consistency, pass whole doc to capture real state of the doc
    from comfort.finance.doctype.payment.payment import Payment

    doc = new_doc(Payment)
    doc.amount = amount
    doc.paid_with_cash = paid_with_cash
    doc.voucher_type = doctype
    doc.voucher_no = name
    doc.insert().submit()
