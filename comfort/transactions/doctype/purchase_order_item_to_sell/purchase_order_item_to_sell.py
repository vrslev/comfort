from __future__ import annotations

from comfort import TypedDocument


class PurchaseOrderItemToSell(TypedDocument):
    item_code: str
    item_name: str | None
    qty: int
    rate: int
    amount: int
    weight: float
    parent: str
