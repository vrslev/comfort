from typing import Any

import pytest

from comfort import get_doc
from comfort.entities import Item
from comfort.stock import StockEntry
from comfort.stock.report.stock_balance.stock_balance import get_data


@pytest.mark.parametrize("v", ({}, {"stock_type": None}))
def test_stock_balance_get_data_no_filter(v: Any):
    assert get_data(v) is None


def test_stock_balance_get_data_with_filter(item_no_children: Item):
    qty = 10
    item_no_children.db_insert()
    get_doc(
        StockEntry,
        {
            "stock_type": "Available Actual",
            "items": [{"item_code": item_no_children.item_code, "qty": qty}],
        },
    ).insert()
    assert get_data(filters={"stock_type": "Available Actual"}) == [
        {
            "item_code": item_no_children.item_code,
            "item_name": item_no_children.item_name,
            "qty": qty,
        }
    ]
