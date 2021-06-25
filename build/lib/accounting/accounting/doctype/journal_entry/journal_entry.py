
import frappe
from frappe.model.document import Document
from frappe import _
from frappe.utils import flt


class JournalEntry(Document):

	def validate(self):
		self.set_total_debit_credit()
		if self.difference:
			frappe.throw(_("Total Debit and Credit must be equal. The difference is {0}").format(
				self.difference))

	def set_total_debit_credit(self):
		self.total_debit, self.total_credit, self.difference = 0, 0, 0
		for d in self.accounting_entries:
			self.total_debit = flt(self.total_debit) + flt(d.debit)
			self.total_credit = flt(self.total_credit) + flt(d.credit)

		self.difference = flt(self.total_debit) - flt(self.total_credit)

	def on_submit(self):
		self.balance_update()
		self.make_gl_entry()

	def on_cancel(self):
		self.make_reverse_gl_entry(voucher_type=self.doctype, voucher_no=self.name)

	def make_reverse_gl_entry(self, voucher_type=None, voucher_no=None):
		gl_entries = frappe.get_all('GL Entry', filters={
									"voucher_type": voucher_type, "voucher_no": voucher_no}, fields=["*"])
		if gl_entries:
			self.cancel_gl_entry(gl_entries[0].voucher_type, gl_entries[0].voucher_no)
			self.adjust_account_balance()

			for entry in gl_entries:
				debit = entry.debit_amount
				credit = entry.credit_amount
				entry.name = None
				entry.debit_amount = credit
				entry.credit_amount = debit
				entry.is_cancelled = 1
				entry.remarks = "Cancelled GL Entry (" + entry.voucher_no + ")"
				entry.balance = frappe.db.get_value(
					'Account', entry.account, 'account_balance')

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

	def adjust_account_balance(self):
		for d in self.accounting_entries:
			account = frappe.get_doc('Account', d.account)
			if aaccount.account_type == 'Asset' or aaccount.account_type == 'Expense':
				if d.debit > 0:
					aaccount.account_balance -= d.debit
				elif d.credit > 0:
					aaccount.account_balance += d.credit
			elif aaccount.account_type == 'Liability' or aaccount.account_type == 'Income':
				if d.debit > 0:
					aaccount.account_balance += d.debit
				elif d.credit > 0:
					aaccount.account_balance -= d.credit
			aaccount.save()

	def balance_update(self):
		for d in self.accounting_entries:
			account = frappe.get_doc('Account', d.account)
			if aaccount.account_type == 'Asset' or aaccount.account_type == 'Expense':
				if d.debit > 0:
					aaccount.account_balance += d.debit
				elif d.credit > 0:
					aaccount.account_balance -= d.credit
			elif aaccount.account_type == 'Liability' or aaccount.account_type == 'Income':
				if d.debit > 0:
					aaccount.account_balance -= d.debit
				elif d.credit > 0:
					aaccount.account_balance += d.credit
			aaccount.save()

	def make_gl_entry(self):
		for d in self.accounting_entries:
			frappe.get_doc({
				'doctype': 'GL Entry',
				'posting_date': self.posting_date,
				'account': d.account,
				'debit_amount': d.debit,
				'credit_amount': d.credit,
				'voucher_type': self.doctype,
				'voucher_no': self.name,
				'party': d.party,
				'balance': frappe.db.get_value('Account', d.account, 'account_balance')
			}).insert()
