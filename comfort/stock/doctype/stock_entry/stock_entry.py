from __future__ import annotations

from typing import Literal

import frappe
from frappe.model.document import Document

from ..stock_entry_item.stock_entry_item import StockEntryItem

_StockType = Literal[
    "Reserved Actual", "Available Actual", "Reserved Purchased", "Available Purchased"
]


class StockEntry(Document):
    stock_type: _StockType
    voucher_type: str | None
    voucher_no: str | None
    items: list[StockEntryItem]

    @staticmethod
    def create_for(  # pragma: no cover
        doctype: str | None,
        name: str | None,
        stock_type: _StockType,
        items: list[StockEntryItem],
    ):
        doc: StockEntry = frappe.get_doc(
            {
                "doctype": "Stock Entry",
                "voucher_type": doctype,
                "voucher_no": name,
                "stock_type": stock_type,
                "items": items,
            }
        )
        doc.insert()
        doc.submit()
        return doc

    @staticmethod
    def cancel_for(doctype: str, name: str):
        entries: list[StockEntry] = frappe.get_all(
            "Stock Entry",
            {"voucher_type": doctype, "voucher_no": name, "docstatus": ("!=", 2)},
        )
        for entry in entries:
            frappe.get_doc("Stock Entry", entry.name).cancel()

    @staticmethod
    def cancel_for_(doctype: str, name: str):
        # TODO: If Sales Order, then create stock entries for Items To Sell
        StockEntry.cancel_for(doctype, name)
        if doctype == "Sales Order":
            ...

        # if self.delivery_status == "To Purchase":
        #     ...  # do nothing
        # elif self.delivery_status == "Purchased":
        #     ...  # reserved_purchased -> available_purchased
        # elif self.delivery_status == "To Deliver":
        #     ...  # remove from reserved_actual
        # elif self.delivery_status == "Delivered":
        #     ...  # add to available_actual
