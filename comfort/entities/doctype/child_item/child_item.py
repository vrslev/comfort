from frappe.model.document import Document


class ChildItem(Document):
    item_code: str
    item_name: str
    qty: int
    parent: str
