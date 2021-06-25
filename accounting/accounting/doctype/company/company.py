
import frappe
from frappe.utils.nestedset import NestedSet

class Company(NestedSet):

	def on_update(self):
		NestedSet.on_update(self)
		if not frappe.db.sql("""SELECT
							name
						FROM
							tabAccount
						WHERE
							company=%s and docstatus<2 limit 1""", self.name):
			self.create_accounts()
		self.set_default_accounts()

	def create_accounts(self):
		from accounting.accounting.doctype.account.chart_of_accounts.chart_of_accounts import create_charts
		frappe.local.flags.ignore_root_company_validation = True
		create_charts(self.name, self.abbr)
	
	def set_default_accounts(self):
		set_default_field(self, 'default_cash_account', 'Cash')
		set_default_field(self, 'default_payable_account', 'Payable')
		set_default_field(self, 'default_receivable_account', 'Receivable')
		set_default_field(self, 'default_cost_of_goods_sold_account', 'Cost of Goods Sold')
		set_default_field(self, 'default_income_account', 'Income Account')
		set_default_field(self, 'default_inventory_account', 'Stock')
		set_default_field(self, 'stock_received_but_not_billed', 'Stock Received But Not Billed')
	
def set_default_field(self, default_account_field, account_type):
	frappe.db.set(self, default_account_field, frappe.db.get_value("Account",
			{"company": self.name, "account_type": account_type, "is_group": 0}))