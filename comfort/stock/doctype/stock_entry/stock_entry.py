from __future__ import annotations

from typing import Literal

import frappe
from comfort.stock.doctype.stock_entry_item.stock_entry_item import StockEntryItem
from comfort.stock.utils import StockTypes
from comfort.utils import TypedDocument


class StockEntry(TypedDocument):
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


def on_doctype_update():
    frappe.db.add_index("Stock Entry", ["voucher_type", "voucher_no"])
