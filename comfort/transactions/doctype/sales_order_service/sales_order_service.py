from frappe.model.document import Document


class SalesOrderService(Document):
    rate: int
    type: str
