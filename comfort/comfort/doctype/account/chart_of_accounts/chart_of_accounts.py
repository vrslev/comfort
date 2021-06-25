
import frappe
from frappe import _
from frappe.utils.nestedset import rebuild_tree
from six import iteritems


def create_charts(company, abbr):
		chart = {
			_("Application of Funds (Assets)"): {
				_("Current Assets"): {
					_("Accounts Receivable"): {
						_("Debtors"): {
							"account_type": "Receivable"
						}
					},
					_("Bank Accounts"): {
						_("Bank"): {
							"account_type": "Bank"
						}
					},
					_("Cash In Hand"): {
						_("Cash"): {
							"account_type": "Cash"
						}
					},
					_("Stock Assets"): {
						_("Stock In Hand"): {
							"account_type": "Stock"
						}
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
					_("Sales"): {
						"account_type": "Income Account"
					}
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

		def _import_accounts(children, parent, root_type, root_account=False):
			for account_name, child in iteritems(children):
				if root_account:
					root_type = child.get("root_type")

				if account_name not in ["account_type",
					"root_type", "is_group"]:
					is_group = identify_is_group(child)
					account_name_with_abbr = account_name + " - " + abbr

					account = frappe.get_doc({
						"doctype": "Account",
						"account_name": account_name_with_abbr,
						"account_type": child.get("account_type"),
						"company": company,
						"parent_account": parent,
						"is_group": is_group,
						"root_type": root_type
					})

					if root_account:
						account.flags.ignore_mandatory = True

					account.flags.ignore_permissions = True

					account.insert()

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
	elif len(set(child.keys()) - set(["account_type", "root_type", "is_group"])):
		is_group = 1
	else:
		is_group = 0

	return is_group
