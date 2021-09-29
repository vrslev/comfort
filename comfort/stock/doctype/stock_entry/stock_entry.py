from __future__ import annotations

from typing import Literal

from comfort.stock import StockTypes
from frappe.model.document import Document

from ..stock_entry_item.stock_entry_item import StockEntryItem


class StockEntry(Document):
    stock_type: StockTypes
    voucher_type: Literal[
        "Receipt",
        "Checkout",
        "Sales Return",
        "Purchase Return",
        "Sales Order",  # Only when `from_available_stock` is "Available Actual"
    ]
    voucher_no: str
    items: list[StockEntryItem]
