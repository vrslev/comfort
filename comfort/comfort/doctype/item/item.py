import frappe
from frappe import _
from frappe.model.document import Document


class Item(Document):
    # TODO: Validate URL
    def validate(self):
        self.validate_child_items()
        self.set_name()
        self.calculate_weight()

    def validate_child_items(self):
        if self.child_items and frappe.db.exists('Child Item', {'parent': ['in', [d.item_code for d in self.child_items]]}):
            frappe.throw(_("Can't add child item that contains child items"))

    def set_name(self):
        if not self.item_name:
            self.item_name = self.item_code

    def calculate_weight(self):
        if not (self.child_items and len(self.child_items) > 0):
            return

        items = frappe.get_all('Item', ['item_code', 'weight'], {
            'item_code': ['in', [d.item_code for d in self.child_items]]})
        weight_map = {}
        for d in items:
            if d.item_code not in weight_map:
                weight_map[d.item_code] = 0
            weight_map[d.item_code] += d.weight

        self.weight = 0
        for d in self.child_items:
            self.weight += weight_map[d.item_code] * d.qty

    def on_update(self):
        self.calculate_weight_in_parent_docs()

    def calculate_weight_in_parent_docs(self):
        parent_items = frappe.get_all('Child Item', 'parent', {
                                      'item_code': self.item_code})
        parent_items = list(set([d.parent for d in parent_items]))
        for d in parent_items:
            doc = frappe.get_doc('Item', d)
            doc.calculate_weight()
            doc.db_update()

    def after_insert(self):
        if self.child_items and len(self.child_items) > 0:
            for d in self.child_items:
                frappe.get_doc('Item', d.item_code).after_insert()
        elif not frappe.db.exists('Bin', self.item_code):
            bin = frappe.new_doc('Bin')
            bin.item_code = self.item_code
            bin.insert()

    def on_trash(self):
        if frappe.db.exists('Bin', self.item_code):
            bin = frappe.get_doc('Bin', self.item_code)
            if (bin.reserved_actual + bin.available_actual + bin.reserved_purchased
                    + bin.available_purchased + bin.projected) > 0:
                frappe.throw(
                    _("Can't delete item that have been used in transactions"))
            else:
                bin.delete()
