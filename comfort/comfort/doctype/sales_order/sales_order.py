import frappe
from comfort.comfort.general_ledger import make_gl_entry, make_reverse_gl_entry
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt


class SalesOrder(Document):
    # TODO: Set statuses
    # TODO: Item query
    # TODO: Make returns
    # TODO: Discount
    # TODO: Services
    # TODO: Hide button "DELIVERED" when PO not recevied yet
    # TODO: Calculate total weight
    def validate(self):
        self.validate_quantity()
        self.set_item_rate_amount()
        self.set_totals()
        self.set_child_items()
        self.set_paid_and_pending_per_amount()
        self.set_delivery_status()
        self.set_payment_status()
        self.set_status()

    def validate_quantity(self):
        for item in self.items:
            if item.qty <= 0:
                frappe.throw(
                    "One or more quantity is required for each product")

    def set_item_rate_amount(self):
        for item in self.items:
            item.rate = frappe.db.get_value(
                'Item', item.item_code, 'rate')
            item.amount = flt(item.qty) * item.rate

    def set_totals(self):
        self.total_quantity, self.total_amount = 0, 0
        for item in self.items:
            self.total_quantity = flt(self.total_quantity) + flt(item.qty)
            self.total_amount = flt(self.total_amount) + flt(item.amount)

    def set_child_items(self):
        self.child_items = []

        items_to_qty_map = {}
        prepared_for_query = []
        for d in self.items:
            prepared_for_query.append(f'"{d.item_code}"')
            if d.item_code not in items_to_qty_map:
                items_to_qty_map[d.item_code] = 0
            items_to_qty_map[d.item_code] += d.qty

        child_items = frappe.db.sql(f'''
            SELECT parent as parent_item_code, item_code, item_name, qty
            FROM `tabChild Item`
            WHERE parent IN ({','.join(prepared_for_query)})
        ''', as_dict=True)

        for d in child_items:
            if d.parent_item_code not in items_to_qty_map:
                continue
            d.qty = d.qty * items_to_qty_map[d.parent_item_code]

        self.extend('child_items', child_items)

    def set_payment_status(self):
        if self.docstatus == 2:
            return

        self.per_paid = int(self.per_paid)

        if self.per_paid > 100:
            status = 'Overpaid'
        elif self.per_paid == 100:
            status = 'Paid'
        elif self.per_paid > 0:
            status = 'Partially Paid'
        else:
            status = 'Unpaid'

        self.db_set('payment_status', status)

    def set_delivery_status(self):
        if self.docstatus == 2 or self.delivery_status == 'Delivered':
            return
        status = None

        po_name = frappe.get_all('Purchase Order Sales Order', 'parent', {
                                 'docstatus': 1, 'sales_order_name': self.name})
        if len(po_name) > 0:
            po_name = po_name[0].parent
            po_status = frappe.get_cached_value(
                'Purchase Order', po_name, 'status')
            if po_status == 'To Receive':
                status = 'Purchased'
            elif po_status == 'Completed':
                status = 'To Deliver'

        if not status:
            status = 'To Purchase'

        self.db_set('delivery_status', status)

    def set_status(self):
        if self.docstatus == 0:
            status = 'Draft'
        elif self.docstatus == 1:
            if self.payment_status == 'Paid' and self.delivery_status == 'Delivered':
                status = 'Completed'
            else:
                status = 'In Progress'
        else:
            status = 'Cancelled'

        self.db_set('status', status)

    def make_delivery_gl_entries(self):
        transaction_type = 'Delivery'
        if frappe.db.exists({
            'doctype': 'GL Entry',
            'transaction_type': transaction_type,
            'voucher_type': self.doctype,
            'voucher_no': self.name
        }):
            frappe.throw(_("Already marked as delivered"))

        company = frappe.db.get_single_value('Defaults', 'default_company')

        income_account = frappe.db.get_value(
            'Company', company, 'default_inventory_account')
        make_gl_entry(self,
                      income_account, 0, self.total_amount, transaction_type)

        debit_to = frappe.db.get_value(
            'Company', company, 'default_cost_of_goods_sold_account')
        make_gl_entry(self, debit_to, self.total_amount, 0, transaction_type)

    def update_actual_qty(self):
        items_map = {}
        for d in self.items:
            if d.item_code not in items_map:
                items_map[d.item_code] = 0
            items_map[d.item_code] += d.qty

        for item_code, qty in items_map.items():
            bin = frappe.get_doc('Bin', item_code)
            bin.actual_qty -= qty
            bin.save()

    @frappe.whitelist()
    def set_delivered(self):
        self.make_delivery_gl_entries()
        self.update_actual_qty()
        self.db_set('delivery_status', 'Delivered')

    def make_invoice_gl_entries(self, paid_amount):
        transaction_type = 'Invoice'

        company = frappe.db.get_single_value('Defaults', 'default_company')

        income_account = frappe.db.get_value(
            'Company', company, 'default_income_account')
        make_gl_entry(self,
                      income_account, 0, paid_amount, transaction_type)

        debit_to = frappe.db.get_value(
            'Company', company, 'default_bank_account')
        make_gl_entry(self, debit_to, paid_amount, 0, transaction_type)

    def set_paid_and_pending_per_amount(self, additional_paid_amount=0):
        self.db_set('paid_amount', self.paid_amount + additional_paid_amount)

        if int(self.total_amount) == 0:
            per_paid = 100
        else:
            per_paid = self.paid_amount / self.total_amount * 100
        self.db_set('per_paid', per_paid)

        self.db_set('pending_amount', self.total_amount - self.paid_amount)

    @frappe.whitelist()
    def set_paid(self, paid_amount):
        if int(self.total_amount) != 0:
            self.make_invoice_gl_entries(paid_amount)

        self.set_paid_and_pending_per_amount(paid_amount)
        self.set_payment_status()

    def on_cancel(self):
        self.ignore_linked_doctypes = ('GL Entry')

        make_reverse_gl_entry(self.doctype, self.name, 'Delivery')
        make_reverse_gl_entry(self.doctype, self.name, 'Invoice')

        self.db_set('paid_amount', 0)
        self.db_set('per_paid', 0)
        self.set_pending_amount()

        self.db_set('payment_status', '')
        self.db_set('delivery_status', '')
