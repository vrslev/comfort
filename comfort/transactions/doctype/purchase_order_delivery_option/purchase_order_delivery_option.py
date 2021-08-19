from datetime import datetime

from frappe.model.document import Document


class PurchaseOrderDeliveryOption(Document):
    type: str
    service_provider: str
    date: datetime
    price: int
    unavailable_items_json: str
