from __future__ import annotations

from typing import Any, Literal

from comfort import count_qty, get_all, get_doc, new_doc
from comfort.stock.doctype.stock_entry_item.stock_entry_item import StockEntryItem

StockTypes = Literal[
    "Reserved Actual", "Available Actual", "Reserved Purchased", "Available Purchased"
]


def create_receipt(doctype: Literal["Sales Order", "Purchase Order"], name: str):
    from comfort.stock.doctype.receipt.receipt import Receipt

    doc = new_doc(Receipt)
    doc.voucher_type = doctype
    doc.voucher_no = name
    doc.insert().submit()


def create_checkout(purchase_order: str):
    from comfort.stock.doctype.checkout.checkout import Checkout

    doc = new_doc(Checkout)
    doc.purchase_order = purchase_order
    doc.insert().submit()


def create_stock_entry(
    doctype: Literal["Receipt", "Checkout", "Sales Return", "Purchase Return"],
    name: str,
    stock_type: StockTypes,
    items: list[Any],
    reverse_qty: bool = False,
):
    from comfort.stock.doctype.stock_entry.stock_entry import StockEntry

    doc = new_doc(StockEntry)
    doc.stock_type = stock_type
    doc.voucher_type = doctype
    doc.voucher_no = name
    doc.extend(
        "items",
        [
            {"item_code": item_code, "qty": -qty if reverse_qty else qty}
            for item_code, qty in count_qty(items).items()
        ],
    )
    doc.insert().submit()


def cancel_stock_entries_for(
    doctype: Literal[
        "Receipt", "Checkout", "Sales Return", "Purchase Return", "Sales Order"
    ],
    name: str,
):
    from comfort.stock.doctype.stock_entry.stock_entry import StockEntry

    entries = get_all(
        StockEntry,
        {"voucher_type": doctype, "voucher_no": name, "docstatus": ("!=", 2)},
    )
    for entry in entries:
        get_doc(StockEntry, entry.name).cancel()


def get_stock_balance(stock_type: StockTypes) -> dict[str, int]:
    from comfort.stock.doctype.stock_entry.stock_entry import StockEntry

    stock_entries = (
        entry.name
        for entry in get_all(
            StockEntry, {"docstatus": ("!=", 2), "stock_type": stock_type}
        )
    )

    items = get_all(
        StockEntryItem,
        fields=("item_code", "qty"),
        filters={"parent": ("in", stock_entries)},
    )

    res: dict[str, int] = {}
    for item_code, qty in count_qty(items).items():
        if qty != 0:
            res[item_code] = qty
    return res
