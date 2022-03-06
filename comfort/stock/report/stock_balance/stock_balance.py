from __future__ import annotations

from typing import TypedDict

from comfort import get_all, group_by_attr
from comfort.entities.doctype.item.item import Item
from comfort.stock.utils import StockTypes, get_stock_balance


class StockBalanceFilters(TypedDict):
    stock_type: StockTypes | None


columns = [
    {
        "fieldname": "item_code",
        "fieldtype": "Link",
        "label": "Item",
        "options": "Item",
        "width": 500,
    },
    {"fieldname": "item_name", "hidden": 1},
    {
        "fieldname": "qty",
        "fieldtype": "Int",
        "label": "Quantity",
        "width": 100,
    },
]


def get_data(filters: StockBalanceFilters):
    if not "stock_type" in filters or not filters["stock_type"]:
        return
    balance = get_stock_balance(filters["stock_type"])
    items_with_names = get_all(
        Item,
        field=("item_code", "item_name"),
        filter={"item_code": ("in", balance.keys())},
    )
    names_map = group_by_attr(items_with_names)
    return [
        {
            "item_code": item_code,
            "item_name": names_map[item_code][0].item_name,
            "qty": qty,
        }
        for item_code, qty in balance.items()
    ]


def execute(filters: StockBalanceFilters):  # pragma: no cover
    return columns, get_data(filters)
