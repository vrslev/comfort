from __future__ import annotations

from datetime import datetime

from comfort import ValidationError, _, get_all
from comfort.finance.doctype.gl_entry.gl_entry import GLEntry


def execute(filters: dict[str, str]):  # pragma: no cover
    validate_filters(filters)
    return get_columns(), get_data(filters)


def validate_filters(filters: dict[str, str]):
    if filters["from_date"] > filters["to_date"]:
        raise ValidationError(_("To Date should be after From Date"))


def get_columns():  # pragma: no cover
    return [
        {
            "label": "GL Entry",
            "fieldname": "gl_entry",
            "fieldtype": "Link",
            "options": "GL Entry",
            "hidden": 1,
        },
        {
            "label": "Date",
            "fieldname": "date",
            "fieldtype": "Date",
            "width": 150,
        },
        {
            "label": "Account",
            "fieldname": "account",
            "fieldtype": "Link",
            "options": "Account",
            "width": 130,
        },
        {
            "label": "Debit",
            "fieldname": "debit",
            "fieldtype": "Currency",
            "width": 110,
        },
        {
            "label": "Credit",
            "fieldname": "credit",
            "fieldtype": "Currency",
            "width": 110,
        },
        {
            "label": "Balance",
            "fieldname": "balance",
            "fieldtype": "Currency",
            "width": 130,
        },
        {
            "label": "Voucher Type",
            "fieldname": "voucher_type",
            "fieldtype": "Data",
            "width": 120,
        },
        {
            "label": "Voucher No",
            "fieldname": "voucher_no",
            "fieldtype": "Dynamic Link",
            "options": "voucher_type",
            "width": 180,
        },
    ]


class _GLEntryForReport(GLEntry):
    gl_entry: str
    date: datetime
    balance: int


def get_data(filters: dict[str, str]) -> list[_GLEntryForReport]:
    return get_all(  # type: ignore
        GLEntry,
        fields=(
            "name as gl_entry",
            "creation as date",
            "account",
            "voucher_type",
            "voucher_no",
            "debit",
            "credit",
            "(debit - credit) as balance",
        ),
        filters=(
            ("docstatus", "!=", 2),
            ("creation", "between", (filters["from_date"], filters["to_date"])),
        ),
        order_by="creation",
    )
