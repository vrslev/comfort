# type: ignore
#
import frappe
from comfort import ValidationError
from frappe import _, _dict
from frappe.utils import flt

# TODO:
# pyright: reportUnknownArgumentType=false, reportUnknownParameterType=false


def execute(filters=None):
    columns, data = [], []

    validate_filters(filters)

    columns = get_columns()
    data = get_data(filters)

    return columns, data


def validate_filters(filters):
    if filters.from_date > filters.to_date:
        raise ValidationError("From Date Should be less than To Date")


def get_columns():
    columns = [
        {
            "label": "GL Entry",
            "fieldname": "gl_entry",
            "fieldtype": "Link",
            "options": "GL Entry",
            "hidden": 1,
        },
        {
            "label": "Posting Date",
            "fieldname": "posting_date",
            "fieldtype": "Date",
            "width": 90,
        },
        {
            "label": "Account",
            "fieldname": "account",
            "fieldtype": "Link",
            "options": "Account",
            "width": 180,
        },
        {
            "label": "Debit (INR)",
            "fieldname": "debit_amount",
            "fieldtype": "Float",
            "width": 100,
        },
        {
            "label": "Credit (INR)",
            "fieldname": "credit_amount",
            "fieldtype": "Float",
            "width": 100,
        },
        {
            "label": "Balance (INR)",
            "fieldname": "balance",
            "fieldtype": "Float",
            "width": 130,
        },
        {"label": "Voucher Type", "fieldname": "voucher_type", "width": 120},
        {
            "label": "Voucher No",
            "fieldname": "voucher_no",
            "fieldtype": "Dynamic Link",
            "options": "voucher_type",
            "width": 180,
        },
        {"label": "Customer", "fieldname": "customer", "width": 100},
    ]
    return columns


def get_data(filters):
    gl_entries = get_gl_entries(filters)
    entries = get_all_entries(filters, gl_entries)
    data = add_balance_in_entries(entries)
    return data


def get_gl_entries(filters):

    gl_entries = frappe.db.sql(
        """
        SELECT name as gl_entry, posting_date, account, customer, voucher_type,
               voucher_no, debit_amount, credit_amount
        FROM `tabGL Entry`
        WHERE %(conditions)s
        ORDER BY voucher_no, account
        """,
        values={"conditions": get_conditions(filters)},
        as_dict=1,
    )

    return gl_entries


def get_conditions(filters):
    conditions = []

    if filters.get("account"):
        conditions.append("account=%(account)s")

    if filters.get("voucher_no"):
        conditions.append("voucher_no=%(voucher_no)s")

    if filters.get("customer"):
        conditions.append("customer = %(customer)s")

    conditions.append("posting_date>=%(from_date)s")
    conditions.append("posting_date<=%(to_date)s")
    conditions.append("is_cancelled=0")

    return "{}".format(" and ".join(conditions)) if conditions else ""


def get_all_entries(filters, gl_entries):
    data = []
    opening_total_closing = get_updated_entries(filters, gl_entries)
    data.append(opening_total_closing.opening)
    data += gl_entries
    data.append(opening_total_closing.total)
    data.append(opening_total_closing.closing)
    return data


def get_updated_entries(filters, gl_entries):
    opening = get_opening_total_closing("Opening")
    total = get_opening_total_closing("Total")
    closing = get_opening_total_closing("Closing (Opening + Total)")

    for gl_entry in gl_entries:
        total.debit_amount += flt(gl_entry.debit_amount)
        total.credit_amount += flt(gl_entry.credit_amount)
        closing.debit_amount += flt(gl_entry.debit_amount)
        closing.credit_amount += flt(gl_entry.credit_amount)

    return _dict(opening=opening, total=total, closing=closing)  # type: ignore


def get_opening_total_closing(label):
    return _dict(account=label, debit_amount=0.0, credit_amount=0.0, balance=0.0)  # type: ignore


def add_balance_in_entries(data):
    balance = 0

    for d in data:
        if not d.posting_date:
            balance = 0
        balance += d.debit_amount - d.credit_amount
        d.balance = balance

    return data
