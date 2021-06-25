

import frappe
import unittest
from frappe.utils import flt, nowdate
from comfort.comfort.doctype.company.test_company import create_company
from comfort.comfort.doctype.journal_entry.test_journal_entry import get_gl_entries

class TestPaymentEntry(unittest.TestCase):

	def setUp(self):
		create_company('_Test Company')

	def test_payment_entry_creation(self):
		pe = make_payment_entry('Dinesh Supplier', 'Pay', 120000, True, False)
		self.assertTrue(get_payment_entry(pe.name))

		pe = make_payment_entry('Rohan', 'Receive', 120000, True, False)
		self.assertTrue(get_payment_entry(pe.name))
	
	def test_payment_entry_validation(self):
		pe = make_payment_entry('Dinesh Supplier', 'Pay', -120000, False, False)
		self.assertRaises(frappe.exceptions.ValidationError, pe.insert)

		pe = make_payment_entry('Rohan', 'Receive', 0, False, False)
		self.assertRaises(frappe.exceptions.ValidationError, pe.insert)

	def test_gl_entry_creation(self):
		for d in [{'payment_type':'Pay', 'party': 'Dinesh Supplier'}, {'payment_type':'Receive', 'party': 'Rohan'}]:
			pe = make_payment_entry(d['party'], d['payment_type'], 120000, True, True)
			gl_entries = get_gl_entries(pe.name, 'Payment Entry')
			self.assertTrue(gl_entries)

			for gle in gl_entries:
				if gle.account == pe.paid_to:
					self.assertEqual(gle.debit_amount, 120000)
					self.assertEqual(gle.credit_amount, 0)
				else:
					self.assertEqual(gle.credit_amount, 120000)
					self.assertEqual(gle.debit_amount, 0)

	def test_reverse_gl_entry(self):
		for d in [{'payment_type':'Pay', 'party': 'Dinesh Supplier'}, {'payment_type':'Receive', 'party': 'Rohan'}]:
			pe = make_payment_entry(d['party'], d['payment_type'], 120000, True, True)
			gl_entries_before = get_gl_entries(pe.name, 'Payment Entry')
			pe.cancel()
			gl_entries_after = get_gl_entries(pe.name, 'Payment Entry')

			# check if number of gl entries is double the gl entries before cancel
			self.assertEqual(len(gl_entries_after)/2, len(gl_entries_before))

			# check if the is_cancelled if True for all entries after cancel
			for gle in gl_entries_after:
				self.assertTrue(gle.is_cancelled)

def make_payment_entry(party, payment_type, paid_amount, save=True, submit=False):
	pe = frappe.new_doc("Payment Entry")
	pe.party = party
	pe.payment_type = payment_type
	pe.paid_amount = paid_amount
	pe.posting_date = nowdate()
	pe.reference_no = '12345'
	pe.reference_date = nowdate()
	pe.company = '_Test Company'

	if save or submit:
		pe.insert()
		if submit:
			pe.submit()
	
	return pe

def get_payment_entry(name):
	return frappe.db.sql(""" SELECT
					*
				FROM
					`tabPayment Entry`
				WHERE
					name=%s """, name, as_dict=1)

