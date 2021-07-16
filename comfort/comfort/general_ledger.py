from typing import Optional

import frappe
from frappe.utils.data import cint


def make_gl_entries(self, account_from, account_to, amount):
    make_gl_entry(self, account_from, 0, amount)
    make_gl_entry(self, account_to, amount, 0)


def make_gl_entry(self, account, dr, cr):
    party = None
    if hasattr(self, "party") and self.get("party"):
        party = self.party
    elif hasattr(self, "customer"):
        party = self.customer

    frappe.get_doc(
        {
            "doctype": "GL Entry",
            "account": account,
            "debit_amount": dr,
            "credit_amount": cr,
            "voucher_type": self.doctype,
            "voucher_no": self.name,
            "party": party,
        }
    ).submit()


def make_reverse_gl_entry(voucher_type=None, voucher_no=None):
    gl_entries = frappe.get_all(
        "GL Entry",
        filters={"voucher_type": voucher_type, "voucher_no": voucher_no},
        fields=["*"],
    )

    if gl_entries:
        cancel_gl_entry(gl_entries[0].voucher_type, gl_entries[0].voucher_no)

        for entry in gl_entries:
            debit = entry.debit_amount
            credit = entry.credit_amount
            entry.name = None
            entry.debit_amount = credit
            entry.credit_amount = debit
            entry.is_cancelled = 1
            entry.remarks = "Cancelled GL Entry (" + entry.voucher_no + ")"

            if entry.debit_amount or entry.credit_amount:
                make_cancelled_gl_entry(entry)


def make_cancelled_gl_entry(entry):
    gl_entry = frappe.new_doc("GL Entry")
    gl_entry.update(entry)
    gl_entry.submit()


def cancel_gl_entry(voucher_type, voucher_no):
    frappe.db.sql(
        """
        UPDATE `tabGL Entry`
        SET is_cancelled=1
        WHERE voucher_type=%s
        AND voucher_no=%s AND is_cancelled=0
        """,
        (voucher_type, voucher_no),
    )


def get_account_balance(accounts, conditions="") -> Optional[int]:
    if isinstance(accounts, str):
        accounts = [accounts]
    accounts = ", ".join(["'" + d + "'" for d in accounts])
    if conditions:
        conditions = "AND " + conditions
    try:
        return cint(
            frappe.db.sql(
                f"""
            SELECT SUM(debit_amount) - SUM(credit_amount)
            FROM `tabGL Entry`
            WHERE is_cancelled=0 and account IN ({accounts})
            {conditions}
            """
            )[0][0]
        )
    except IndexError:
        pass


def get_account(field_names):
    return_str = False
    if isinstance(field_names, str):
        field_names = [field_names]
        return_str = True
    settings_name = "Accounts Settings"
    settings = frappe.get_cached_doc(settings_name, settings_name)
    accounts = []
    for d in field_names:
        account = f"default_{d}_account"
        if hasattr(settings, account):
            accounts.append(getattr(settings, account))

    return accounts[0] if return_str else accounts


def get_paid_amount(dt, dn):
    accounts = get_account(["cash", "bank"])
    balance = get_account_balance(
        accounts, f"voucher_type='{dt}' AND voucher_no='{dn}'"
    )
    if balance:
        return balance if dt != "Purchase Order" else -balance
