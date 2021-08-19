from frappe.model.document import Document


class PurchaseOrderSalesOrder(Document):
    sales_order_name: str
    customer: str
    total: int
