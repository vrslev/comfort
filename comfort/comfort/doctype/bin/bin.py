from frappe.model.document import Document


class Bin(Document):
    def before_insert(self):
        for d in ["reserved_actual", "available_actual", "reserved_purchased",
                  "available_purchased", "projected"]:
            if not hasattr(self, d):
                setattr(self, d, 0)
