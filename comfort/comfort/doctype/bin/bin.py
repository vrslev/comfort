from frappe import _
from frappe.model.document import Document

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

