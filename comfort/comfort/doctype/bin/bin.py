import frappe
from frappe import ValidationError, _
from frappe.model.document import Document
from frappe.utils.data import cint

fields = [
    "reserved_actual",
    "available_actual",
    "reserved_purchased",
    "available_purchased",
    "projected",
]


class Bin(Document):
    def before_insert(self):
        for d in fields:
            if not hasattr(self, d):
                setattr(self, d, 0)


def update_bin(item_code: str, **kwargs):
    doc = frappe.get_doc("Bin", item_code)

    for d in kwargs:
        if d not in fields:
            raise ValidationError(_(f"No such argument in Bin: {d}"))

    for attr, qty in kwargs.items():
        new_qty = cint(getattr(doc, attr)) + cint(qty)
        setattr(doc, attr, new_qty)

    doc.save()
