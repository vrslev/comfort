from __future__ import annotations

from comfort.utils import TypedDocument


class ChildItem(TypedDocument):
    item_code: str
    item_name: str | None
    qty: int
    parent: str
