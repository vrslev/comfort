from frappe.model.document import Document


class SalesOrderItem(Document):
    item_code: str
    item_name: str
    qty: int
    rate: int
    amount: int
    weight: float
    total_weight: float
