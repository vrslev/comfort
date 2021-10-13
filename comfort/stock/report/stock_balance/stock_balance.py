from __future__ import annotations

from typing import TypedDict

from comfort import get_all, group_by_attr
from comfort.entities.doctype.item.item import Item
from comfort.stock import StockTypes, get_stock_balance


class StockBalanceFilters(TypedDict):
    stock_type: StockTypes


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
    balance = get_stock_balance(filters["stock_type"])
    items_with_names = get_all(
        Item,
        fields=("item_code", "item_name"),
        filters={"item_code": ("in", balance.keys())},
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
