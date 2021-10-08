from __future__ import annotations

from typing import Literal

from comfort import TypedDocument


class DeliveryStop(TypedDocument):
    sales_order: str
    customer: str
    address: str | None
    phone: str | None
    pending_amount: int
    city: str | None
    details: str | None
    delivery_type: Literal["To Apartment", "To Entrance"] | None
    installation: bool
