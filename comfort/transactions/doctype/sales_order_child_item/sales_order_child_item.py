from frappe.model.document import Document


class SalesOrderChildItem(Document):
    parent_item_code: str
    item_code: str
    item_name: str
    qty: int
    parent: str
