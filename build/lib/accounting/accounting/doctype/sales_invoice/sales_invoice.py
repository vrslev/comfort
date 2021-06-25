
import frappe
from frappe.model.document import Document

class SalesInvoice(Document):

	def on_submit(self):
		self.balance_update(self.income_account, "credit")
		self.balance_update(self.debit_to, "debit")
		self.make_gl_entry(self.income_account, 0, self.total_amount, self.doctype)
		self.make_gl_entry(self.debit_to, self.total_amount, 0, self.doctype)

	def on_cancel(self):
		self.make_reverse_gl_entry(voucher_type=self.doctype, voucher_no=self.name)

	def make_reverse_gl_entry(self, voucher_type=None, voucher_no=None):
		gl_entries = frappe.get_all('GL Entry', filters={"voucher_type": voucher_type, "voucher_no": voucher_no}, fields=["*"])
		if gl_entries:
			self.cancel_gl_entry(gl_entries[0].voucher_type, gl_entries[0].voucher_no)
			self.balance_update(self.income_account, "debit")
			self.balance_update(self.debit_to, "credit")

			for entry in gl_entries:
				debit = entry.debit_amount
				credit = entry.credit_amount
				entry.name = None
				entry.debit_amount = credit
				entry.credit_amount = debit
				entry.is_cancelled = 1
				entry.remarks = "Cancelled GL Entry ("+ entry.voucher_no +")"
				entry.balance= frappe.db.get_value('Account', entry.account, 'account_balance')
				
				if entry.debit_amount or entry.credit_amount:
					self.make_cancelled_gl_entry(entry)

	def make_cancelled_gl_entry(self, entry):
		gl_entry = frappe.new_doc('GL Entry')
		gl_entry.update(entry)
		gl_entry.insert()
		gl_entry.submit()

	def cancel_gl_entry(self, voucher_type, voucher_no):
		frappe.db.sql("""UPDATE
				`tabGL Entry`
			SET
				is_cancelled=1 
			WHERE
				voucher_type=%s and voucher_no=%s and is_cancelled=0""",
			(voucher_type, voucher_no))

	def balance_update(self, account, type):
		account = frappe.get_doc('Account', account)
		if type == "debit":
			account.account_balance += self.total_amount
		elif type == "credit":
			account.account_balance -= self.total_amount
		account.save()

	def make_gl_entry(self, account, dr, cr, doctype):
		frappe.get_doc({
			'doctype': 'GL Entry',
			'posting_date': self.posting_date,
			'account': account,
			'debit_amount': dr,
			'credit_amount': cr,
			'voucher_type': doctype,
			'voucher_no': self.name,
			'party': self.party,
			'balance': frappe.db.get_value('Account', account, 'account_balance')
		}).insert()

@frappe.whitelist()
def make_payment_entry(source_name, target_doc=None):
	from frappe.model.mapper import get_mapped_doc

	doclist = get_mapped_doc("Sales Invoice", source_name , {
		"Sales Invoice": {
			"doctype": "Payment Entry",
			"field_map": {
				"total_amount": "paid_amount",
				"debit_to": "paid_from"
			},
			"validation": {
				"docstatus": ["=", 1]
			}
		}
	}, target_doc)

	return doclist