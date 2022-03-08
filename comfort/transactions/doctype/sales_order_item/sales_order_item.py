from __future__ import annotations

from comfort.utils import TypedDocument


class SalesOrderItem(TypedDocument):
    item_code: str
    item_name: str | None
    qty: int
    rate: int
    amount: int
    weight: float
    total_weight: float
    parent: str
