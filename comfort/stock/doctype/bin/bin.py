from frappe import _
from frappe.model.document import Document

BIN_FIELDS = [
    "reserved_actual",
    "available_actual",
    "reserved_purchased",
    "available_purchased",
    "projected",
]


class Bin(Document):
    item_code: str

    def before_insert(self):  # pragma: no cover
        self.fill_with_nulls()

    def fill_with_nulls(self):
        for f in BIN_FIELDS:
            if getattr(self, f) is None:
                setattr(self, f, 0)

    @property
    def is_empty(self):
        count = 0
        for f in BIN_FIELDS:
            count += getattr(self, f)
        return count == 0
