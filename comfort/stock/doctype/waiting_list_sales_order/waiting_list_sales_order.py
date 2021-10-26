from __future__ import annotations

from comfort import TypedDocument


class WaitingListSalesOrder(TypedDocument):
    sales_order: str
    customer: str
    options_changed: bool
    last_options: str | None
    current_options: str | None
