import frappe
from frappe import _
from frappe.model.document import Document


class Bin(Document):
    item_code: str
    reserved_actual: int
    available_actual: int
    reserved_purchased: int
    available_purchased: int

    def before_insert(self):  # pragma: no cover
        self.fill_with_nulls()

    def fill_with_nulls(self):
        def set_null_if_none(value: int):
            return 0 if value is None else value

        self.reserved_actual = set_null_if_none(self.reserved_actual)
        self.available_actual = set_null_if_none(self.available_actual)
        self.reserved_purchased = set_null_if_none(self.reserved_purchased)
        self.available_purchased = set_null_if_none(self.available_purchased)

    @property
    def projected(self):
        return (
            self.available_actual
            + self.available_purchased
            - self.reserved_actual
            - self.reserved_purchased
        )

    @property
    def is_empty(self):
        for field in [
            self.reserved_actual,
            self.available_actual,
            self.reserved_purchased,
            self.available_purchased,
        ]:
            if field > 0:
                return False
        return True

    @staticmethod
    def update_for(
        item_code: str,
        reserved_actual: int = 0,
        available_actual: int = 0,
        reserved_purchased: int = 0,
        available_purchased: int = 0,
    ):
        doc: Bin = frappe.get_doc("Bin", item_code)
        doc.reserved_actual += reserved_actual
        doc.available_actual += available_actual
        doc.reserved_purchased += reserved_purchased
        doc.available_purchased += available_purchased
        doc.save()
