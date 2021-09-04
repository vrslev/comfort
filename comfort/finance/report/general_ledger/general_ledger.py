from __future__ import annotations

from typing import Any

import frappe
from comfort import ValidationError
from frappe import _


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


def get_data(filters: dict[str, str]):
    entries: list[Any] = frappe.get_all(
        "GL Entry",
        fields=(
            "name as gl_entry",
            "creation as date",
            "account",
            "voucher_type",
            "voucher_no",
            "debit",
            "credit",
        ),
        filters=(
            ("docstatus", "!=", 2),
            ("creation", "between", (filters["from_date"], filters["to_date"])),
        ),
        order_by="creation",
    )
    for entry in entries:
        entry.balance = entry.debit - entry.credit
    return entries
