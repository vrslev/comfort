from frappe.model.document import Document


class StockEntryItem(Document):
    item_code: str
    qty: int
