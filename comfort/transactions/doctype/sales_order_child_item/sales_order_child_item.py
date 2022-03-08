from __future__ import annotations

from comfort.utils import TypedDocument


class SalesOrderChildItem(TypedDocument):
    parent_item_code: str
    item_code: str
    item_name: str | None
    qty: int
    parent: str
