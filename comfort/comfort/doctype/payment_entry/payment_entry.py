import frappe
from comfort.comfort.general_ledger import make_gl_entry, make_reverse_gl_entry
from frappe.model.document import Document


class PaymentEntry(Document):

    def validate(self):
        self.validate_amount()
        self.set_accounts()

    def validate_amount(self):
        if not self.paid_amount or self.paid_amount <= 0:
            frappe.throw("Paid Amount cannot be negative or 0")

    def set_accounts(self):
        if not self.paid_from:
            if self.payment_type == 'Pay':
                self.paid_from = frappe.db.get_value(
                    'Company', self.company, 'default_bank_account')
            else:
                self.paid_from = frappe.db.get_value(
                    'Company', self.company, 'default_receivable_account')
        if not self.paid_to:
            if self.payment_type == 'Pay':
                self.paid_to = frappe.db.get_value(
                    'Company', self.company, 'default_payable_account')
            else:
                self.paid_to = frappe.db.get_value(
                    'Company', self.company, 'default_bank_account')

    def on_submit(self):
        make_gl_entry(self, self.paid_from, 0, self.paid_amount)
        make_gl_entry(self, self.paid_to, self.paid_amount, 0)

    def on_cancel(self):
        self.ignore_linked_doctypes = ('GL Entry')
        make_reverse_gl_entry(voucher_type=self.doctype, voucher_no=self.name)
