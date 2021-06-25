

import frappe
import unittest


def create_accounts():
	if not frappe.db.exists('Account', 'Company Root'):
		frappe.get_doc({
			'doctype': 'Account',
			'account_name': 'Company Root',
			'is_group': 1
		}).insert(ignore_mandatory=True)

	if not frappe.db.exists('Account', 'Application of Funds (Assets)'):
		frappe.get_doc({
			'doctype': 'Account',
			'account_name': 'Application of Funds (Assets)',
			'parent_account': 'Company Root',
			'is_group': 1
		}).insert()

		frappe.get_doc({
			'doctype': 'Account',
			'account_name': 'Debtors (Receivables)',
			'parent_account': 'Application of Funds (Assets)',
			'is_group': 0
		}).insert()
		frappe.get_doc({
			'doctype': 'Account',
			'account_name': 'Stock in Hand',
			'parent_account': 'Application of Funds (Assets)',
			'is_group': 0
		}).insert()
		frappe.get_doc({
			'doctype': 'Account',
			'account_name': 'Cash',
			'parent_account': 'Application of Funds (Assets)',
			'is_group': 0
		}).insert()

	if not frappe.db.exists('Account', 'Source of Funds (Liabilities)'):
		frappe.get_doc({
			'doctype': 'Account',
			'account_name': 'Source of Funds (Liabilities)',
			'parent_account': 'Company Root',
			'is_group': 1
		}).insert()

		frappe.get_doc({
			'doctype': 'Account',
			'account_name': 'Creditors (Payables)',
			'parent_account': 'Source of Funds (Liabilities)',
			'is_group': 0
		}).insert()

	if not frappe.db.exists('Account', 'Expenses'):
		frappe.get_doc({
			'doctype': 'Account',
			'account_name': 'Expenses',
			'parent_account': 'Company Root',
			'is_group': 1
		}).insert()

	if not frappe.db.exists('Account', 'Income'):
		frappe.get_doc({
			'doctype': 'Account',
			'account_name': 'Income',
			'parent_account': 'Company Root',
			'is_group': 1
		}).insert()


class TestAccount(unittest.TestCase):
	def setUp(self):
		create_accounts()

	def test_rename_account(self):
		if not frappe.db.exists("Account", "test_rename_account"):
			frappe.get_doc({
				'doctype': 'Account',
				'account_name': "test_rename_account",
				'parent_account': "Application of Funds (Assets)",
				'account_number': "1210"
			}).insert()

		doc = frappe.get_doc("Account", "test_rename_account")

		frappe.rename_doc('Account', 'test_rename_account',
						'new_test_rename_account', force=1)

		self.assertEqual(doc.account_number, "1210")
		self.assertEqual(doc.account_name, "test_rename_account")
		frappe.delete_doc('Account', 'new_test_rename_account')