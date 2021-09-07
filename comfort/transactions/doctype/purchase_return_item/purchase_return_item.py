from frappe.model.document import Document


class PurchaseReturnItem(Document):
    item_code: str
    item_name: str
    qty: int
    rate: int
    amount: int
