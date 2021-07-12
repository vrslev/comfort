import unittest

import frappe
from frappe.utils import nowdate

from comfort.comfort.doctype.account.test_account import create_account


class TestJournalEntry(unittest.TestCase):
    def setUp(self):
        create_account(
            "_Test Company", "Capital Stock - _C", "Asset", "Bank", "Equity - _C"
        )
        create_account(
            "_Test Company", "SBI - _C", "Asset", "Bank", "Bank Accounts - _C"
        )

    def test_jv_validate_error(self):
        jv = make_journal_entry(
            nowdate(), "Capital Stock - _C", "SBI - _C", 10000, False, False
        )
        # Check if validation error raises if Dr is not equal to Cr
        jv.accounting_entries[0].update({"credit": 20000})
        self.assertRaises(frappe.exceptions.ValidationError, jv.insert)

        jv.accounting_entries[0].update({"credit": 10000})
        jv.insert()
        jv.delete()

    def test_jv_creation(self):
        jv = make_journal_entry(
            nowdate(), "Capital Stock - _C", "SBI - _C", 10000, True, True
        )
        jv_entry = get_journal_entry(jv.name)
        self.assertTrue(jv_entry)

    def test_gl_entry_creation(self):
        jv = make_journal_entry(
            nowdate(), "Capital Stock - _C", "SBI - _C", 10000, True, True
        )
        gl_entries = get_gl_entries(jv.name, "Journal Entry")
        self.assertTrue(gl_entries)

        for gle in gl_entries:
            if gle.account == "Capital Stock - _C":
                self.assertEqual(gle.debit_amount, 0)
                self.assertEqual(gle.credit_amount, 10000)
            else:
                self.assertEqual(gle.credit_amount, 0)
                self.assertEqual(gle.debit_amount, 10000)

    def test_reverse_gl_entry(self):
        jv = make_journal_entry(
            nowdate(), "Capital Stock - _C", "SBI - _C", 10000, True, True
        )
        gl_entries_before = get_gl_entries(jv.name, "Journal Entry")
        jv.cancel()
        gl_entries_after = get_gl_entries(jv.name, "Journal Entry")

        # check if number of gl entries is double the gl entries before cancel
        self.assertEqual(len(gl_entries_after) / 2, len(gl_entries_before))

        # check if the is_cancelled if True for all entries after cancel
        for gle in gl_entries_after:
            self.assertTrue(gle.is_cancelled)


def make_journal_entry(
    posting_date, account1, account2, amount, save=True, submit=False
):
    jv = frappe.new_doc("Journal Entry")
    jv.posting_date = posting_date or nowdate()
    jv.set(
        "accounting_entries",
        [
            {
                "account": account1,
                "credit": amount if amount > 0 else 0,
                "debit": abs(amount) if amount < 0 else 0,
            },
            {
                "account": account2,
                "debit": amount if amount > 0 else 0,
                "credit": abs(amount) if amount < 0 else 0,
            },
        ],
    )
    if save or submit:
        jv.insert()

        if submit:
            jv.submit()

    return jv


def get_journal_entry(jv_name):
    return frappe.db.sql(
        """ SELECT
						*
					FROM
						`tabJournal Entry`
					WHERE
						name=%s """,
        jv_name,
        as_dict=1,
    )


def get_gl_entries(voucher_no, voucher_type):
    return frappe.db.sql(
        """ SELECT
						*
					FROM
						`tabGL Entry`
					WHERE
						voucher_no=%s and voucher_type=%s """,
        (voucher_no, voucher_type),
        as_dict=1,
    )
