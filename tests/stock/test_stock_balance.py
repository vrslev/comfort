from comfort import get_doc
from comfort.entities.doctype.item.item import Item
from comfort.stock.doctype.stock_entry.stock_entry import StockEntry
from comfort.stock.report.stock_balance.stock_balance import get_data


def test_stock_balance_get_data(item: Item):
    qty = 10
    item.db_insert()
    get_doc(
        StockEntry,
        {
            "stock_type": "Available Actual",
            "items": [{"item_code": item.item_code, "qty": qty}],
        },
    ).insert()
    assert get_data(filters={"stock_type": "Available Actual"}) == [
        {"item_code": item.item_code, "item_name": item.item_name, "qty": qty}
    ]
