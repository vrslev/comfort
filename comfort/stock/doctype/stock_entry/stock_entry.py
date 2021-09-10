from __future__ import annotations

from typing import Literal

from comfort.stock import StockTypes
from frappe.model.document import Document

from ..stock_entry_item.stock_entry_item import StockEntryItem


class StockEntry(Document):
    stock_type: StockTypes
    voucher_type: Literal["Receipt", "Checkout", "Sales Return", "Purchase Return"]
    voucher_no: str
    items: list[StockEntryItem]

    # TODO: If Sales Order, then create stock entries for Items To Sell
    # if self.delivery_status == "To Purchase":
    #     ...  # do nothing
    # elif self.delivery_status == "Purchased":
    #     ...  # reserved_purchased -> available_purchased
    # elif self.delivery_status == "To Deliver":
    #     ...  # remove from reserved_actual
    # elif self.delivery_status == "Delivered":
    #     ...  # add to available_actual
