
import frappe, os, json
from frappe.utils import cstr
from unidecode import unidecode
from six import iteritems
from frappe.utils.nestedset import rebuild_tree
from frappe import _

def create_charts(company):
		chart = {
			_("Application of Funds (Assets)"): {
				_("Current Assets"): {
					_("Accounts Receivable"): {
						_("Debtors"): {
							"account_type": "Receivable"
						}
					},
					_("Bank Accounts"): {
						"account_type": "Bank",
						"is_group": 1
					},
					_("Cash In Hand"): {
						_("Cash"): {
							"account_type": "Cash"
						},
						"account_type": "Cash"
					},
					_("Stock Assets"): {
						_("Stock In Hand"): {
							"account_type": "Stock"
						},
						"account_type": "Stock",
					}
				},
				"root_type": "Asset"
			},
			_("Expenses"): {
				_("Direct Expenses"): {
					_("Stock Expenses"): {
						_("Cost of Goods Sold"): {
							"account_type": "Cost of Goods Sold"
						}
					},
				},
				"root_type": "Expense"
			},
			_("Income"): {
				_("Direct Income"): {
					_("Sales"): {}
				},
				_("Indirect Income"): {
					"is_group": 1
				},
				"root_type": "Income"
			},
			_("Source of Funds (Liabilities)"): {
				_("Current Liabilities"): {
					_("Accounts Payable"): {
						_("Creditors"): {
							"account_type": "Payable"
						},
						_("Payroll Payable"): {},
					},
					_("Stock Liabilities"): {
						_("Stock Received But Not Billed"): {
							"account_type": "Stock Received But Not Billed"
						},
						_("Asset Received But Not Billed"): {
							"account_type": "Asset Received But Not Billed"
						}
					}
				},
				"root_type": "Liability"
			},
			_("Equity"): {
				_("Capital Stock"): {
					"account_type": "Equity"
				},
				"root_type": "Equity"
			}
		}
		accounts = []

		def _import_accounts(children, parent, root_type, root_account=False):
			for account_name, child in iteritems(children):
				if root_account:
					root_type = child.get("root_type")

				if account_name not in ["account_number",
					"root_type", "is_group"]:

					account_number = cstr(child.get("account_number")).strip()
					account_name, account_name_in_db = add_suffix_if_duplicate(account_name,
						account_number, accounts)

					is_group = identify_is_group(child)

					account = frappe.get_doc({
						"doctype": "Account",
						"account_name": account_name,
						"company": company,
						"parent_account": parent,
						"is_group": is_group,
						"root_type": root_type,
						"account_number": account_number
					})

					if root_account or frappe.local.flags.allow_unverified_charts:
						account.flags.ignore_mandatory = True

					account.flags.ignore_permissions = True

					account.insert()

					accounts.append(account_name_in_db)

					_import_accounts(child, account.name, root_type)

		# Rebuild NestedSet HSM tree for Account Doctype
		# after all accounts are already inserted.
		frappe.local.flags.ignore_on_update = True
		_import_accounts(chart, None, None, root_account=True)
		rebuild_tree("Account", "parent_account")
		frappe.local.flags.ignore_on_update = False

def identify_is_group(child):
	if child.get("is_group"):
		is_group = child.get("is_group")
	elif len(set(child.keys()) - set(["account_type", "root_type", "is_group", "account_number"])):
		is_group = 1
	else:
		is_group = 0

	return is_group


def add_suffix_if_duplicate(account_name, account_number, accounts):
	if account_number:
		account_name_in_db = unidecode(" - ".join([account_number,
			account_name.strip().lower()]))
	else:
		account_name_in_db = unidecode(account_name.strip().lower())

	if account_name_in_db in accounts:
		count = accounts.count(account_name_in_db)
		account_name = account_name + " " + cstr(count)

	return account_name, account_name_in_db