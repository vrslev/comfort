from __future__ import annotations

from typing import Literal

from comfort import ValidationError, _, get_all, get_cached_value, get_doc, new_doc


def get_account(field_name: str) -> str:
    name = f"{field_name}_account"

    if account := get_cached_value("Finance Settings", "Finance Settings", name):
        return account

    raise ValidationError(_('Finance Settings has no field "{}"').format(name))


def create_gl_entry(
    doctype: Literal[
        "Payment",
        "Receipt",
        "Sales Return",
        "Purchase Return",
        "Compensation",
        "Money Transfer",
    ],
    name: str,
    account: str,
    debit: int,
    credit: int,
) -> None:
    from comfort.finance.doctype.gl_entry.gl_entry import GLEntry

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
) -> None:
    from comfort.finance.doctype.gl_entry.gl_entry import GLEntry

    for entry in get_all(
        GLEntry,
        filter={"voucher_type": doctype, "voucher_no": name, "docstatus": ("!=", 2)},
    ):
        get_doc(GLEntry, entry.name).cancel()


def create_payment(
    doctype: Literal["Sales Order", "Purchase Order"],
    name: str,
    amount: int,
    paid_with_cash: bool,
) -> None:

    from comfort.finance import Payment

    doc = new_doc(Payment)
    doc.amount = amount
    doc.paid_with_cash = paid_with_cash
    doc.voucher_type = doctype
    doc.voucher_no = name
    doc.insert().submit()
