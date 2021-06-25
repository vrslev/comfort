import frappe
from frappe import _
from frappe.model.document import Document


class Item(Document):
    # TODO: Calculate total weight
    def validate(self):
        if not self.item_name:
            self.item_name = self.item_code
        self.validate_child_items()
        if self.child_items and len(self.child_items) > 0:
            self.has_child_items = True

    def validate_child_items(self):
        if frappe.db.exists('Child Item', {'parent': ['in', [d.item_code for d in self.child_items]]}):
            frappe.throw(_("Can't add child item that contains child items"))

    def after_insert(self):
        if self.child_items and len(self.child_items) > 0:
            for d in self.child_items:
                frappe.get_doc('Item', d.item_code).after_insert()
        elif not frappe.db.exists('Bin', self.item_code):
            bin = frappe.new_doc('Bin')
            bin.item_code = self.item_code
            bin.insert()

    def on_trash(self):
        bin = frappe.get_doc('Bin', self.item_code)
        if (bin.actual + bin.available_actual + bin.ordered
                + bin.available_ordered + bin.projected) > 0:
            frappe.throw(
                _("Can't delete item that have been used in transactions"))
        else:
            bin.delete()
