from datetime import datetime

from comfort.utils import TypedDocument


class PurchaseOrderDeliveryOption(TypedDocument):
    is_available: bool
    type: str
    service_provider: str
    date: datetime
    price: int
    unavailable_items_json: str
