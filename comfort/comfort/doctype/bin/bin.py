import frappe
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


def update_bin(item_code, **kwargs):
    for d in fields:
        if d not in kwargs:
            kwargs[d] = 0

    doc = frappe.get_doc("Bin", item_code)

    for key, value in kwargs.items():
        setattr(doc, key, cint(getattr(doc, key)) + cint(value))

    doc.save()
