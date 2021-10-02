from typing import Literal

from comfort import TypedDocument


class SalesOrderService(TypedDocument):
    type: Literal["Delivery to Apartment", "Delivery to Entrance", "Installation"]
    rate: int
