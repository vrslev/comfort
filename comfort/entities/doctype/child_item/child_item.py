from frappe.model.document import Document


class ChildItem(Document):
    item_code: str
    parent: str
    parent_item_code: str
    qty: int
