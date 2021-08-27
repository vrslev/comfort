from __future__ import annotations

from typing import Literal

from frappe.model.document import Document


class DeliveryStop(Document):
    sales_order: str
    customer: str
    address: str | None
    phone: str | None
    pending_amount: int
    city: str | None
    details: str | None
    delivery_type: Literal["To Apartment", "To Entrance"]
    installation: bool
