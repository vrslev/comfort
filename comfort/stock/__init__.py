from __future__ import annotations

from typing import Literal

import frappe
from comfort import OrderTypes, count_quantity
from comfort.stock.doctype.stock_entry_item.stock_entry_item import StockEntryItem
from frappe.model.document import Document

StockTypes = Literal[
    "Reserved Actual", "Available Actual", "Reserved Purchased", "Available Purchased"
]


def create_receipt(doctype: OrderTypes, name: str):
    doc: Document = frappe.get_doc(
        {"doctype": "Receipt", "voucher_type": doctype, "voucher_no": name}
    )
    doc.insert()
    doc.submit()


def create_checkout(purchase_order: str):
    doc: Document = frappe.get_doc(
        {"doctype": "Checkout", "purchase_order": purchase_order}
    )
    doc.insert()
    doc.submit()


def create_stock_entry(
    doctype: Literal["Receipt", "Checkout", "Sales Return", "Purchase Return"],
    name: str,
    stock_type: StockTypes,
    items: list[object],
    reverse_qty: bool = False,
):
    doc: Document = frappe.get_doc(
        {
            "doctype": "Stock Entry",
            "voucher_type": doctype,
            "voucher_no": name,
            "stock_type": stock_type,
            "items": [
                {"item_code": item_code, "qty": -qty if reverse_qty else qty}
                for item_code, qty in count_quantity(items).items()
            ],
        }
    )
    doc.insert()
    doc.submit()


def cancel_stock_entries_for(doctype: Literal["Checkout", "Receipt"], name: str):
    entries: list[Document] = frappe.get_all(
        "Stock Entry",
        {"voucher_type": doctype, "voucher_no": name, "docstatus": ("!=", 2)},
    )
    for entry in entries:
        doc: Document = frappe.get_doc("Stock Entry", entry.name)
        doc.cancel()


def get_stock_balance(stock_type: StockTypes) -> dict[str, int]:
    stock_entries: list[str] = [
        entry.name
        for entry in frappe.get_all(
            "Stock Entry", {"docstatus": ("!=", 2), "stock_type": stock_type}
        )
    ]
    items: list[StockEntryItem] = frappe.get_all(
        "Stock Entry Item",
        fields=("item_code", "qty"),
        filters={"parent": ("in", stock_entries)},
    )

    res: dict[str, int] = {}
    for item_code, qty in count_quantity(items).items():
        if qty != 0:
            res[item_code] = qty
    return res
