
import frappe
from frappe.utils.nestedset import NestedSet

class Company(NestedSet):
	
	def on_update(self):
		NestedSet.on_update(self)
		self.create_accounts()

	def create_accounts(self):
		from accounting.accounting.doctype.account.chart_of_accounts.chart_of_accounts import create_charts
		frappe.local.flags.ignore_root_company_validation = True
		create_charts(self.name)
		# append_abbr = " - "+ self.abbr

		# list_of_accounts = [
		# 	{'account_name': 'Application of Funds (Assets)'+append_abbr, 'parent_account': '', 'is_group': 1, 'account_type': 'Asset'},
		# 	{'account_name': 'Source of Funds (Liabilities)'+append_abbr, 'parent_account': '', 'is_group': 1, 'account_type': 'Liability'},
		# 	{'account_name': 'Income'+append_abbr, 'parent_account': '', 'is_group': 1, 'account_type': 'Income'},
		# 	{'account_name': 'Expense'+append_abbr, 'parent_account': '', 'is_group': 1, 'account_type': 'Expense'},

		# 	{'account_name': 'Cash'+append_abbr, 'parent_account': 'Application of Funds (Assets)'+append_abbr, 'is_group': 0, 'account_type': 'Asset'},
		# 	{'account_name': 'Debtors (Receivables)'+append_abbr, 'parent_account': 'Application of Funds (Assets)'+append_abbr, 'is_group': 0, 'account_type': 'Asset'},
		# 	{'account_name': 'Stock in Hand'+append_abbr, 'parent_account': 'Application of Funds (Assets)'+append_abbr, 'is_group': 0, 'account_type': 'Asset'},

		# 	{'account_name': 'Creditors (Payables)'+append_abbr, 'parent_account': 'Source of Funds (Liabilities)'+append_abbr, 'is_group': 0, 'account_type': 'Liability'},
		# 	{'account_name': 'Stock Received But Not Billed'+append_abbr, 'parent_account': 'Source of Funds (Liabilities)'+append_abbr, 'is_group': 0, 'account_type': 'Liability'},

		# 	{'account_name': 'Sales'+append_abbr, 'parent_account': 'Income'+append_abbr, 'is_group': 0, 'account_type': 'Income'},

		# 	{'account_name': 'Cost of Goods Sold'+append_abbr, 'parent_account': 'Expense'+append_abbr, 'is_group': 0, 'account_type': 'Expense'},
		# ]

		# for account in list_of_accounts:
		# 	frappe.db.({
		# 		'doctype': 'Account',
		# 		'account_name': account.account_name,
		# 		'account_type': account.account_type,
		# 		'parent_account': account.parent_account,
		# 		'is_group': account.is_group
		# 	}).insert(ignore_mandatory=True)