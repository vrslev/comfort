from typing import Literal

from frappe.model.document import Document


class SalesOrderService(Document):
    type: Literal["Delivery to Apartment", "Delivery to Entrance", "Installation"]
    rate: int
