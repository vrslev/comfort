from datetime import datetime

from comfort import TypedDocument


class PurchaseOrderDeliveryOption(TypedDocument):
    type: str
    service_provider: str
    date: datetime
    price: int
    unavailable_items_json: str
