from __future__ import annotations

from collections import Counter
from types import SimpleNamespace

import pytest

from comfort.stock import Receipt, StockEntry
from comfort.stock.utils import (
    cancel_stock_entries_for,
    create_checkout,
    create_receipt,
    create_stock_entry,
    get_stock_balance,
)
from comfort.transactions import PurchaseOrder, SalesOrder
from comfort.utils import count_qty, counters_are_same, get_all, get_doc, get_value


def test_create_receipt(sales_order: SalesOrder):
    sales_order.db_insert()
    sales_order.db_update_all()
    create_receipt(sales_order.doctype, sales_order.name)
    docstatus: int = get_value(
        "Receipt",
        fieldname="docstatus",
        filters={"voucher_type": sales_order.doctype, "voucher_no": sales_order.name},
    )
    assert docstatus == 1


def test_create_checkout(purchase_order: PurchaseOrder):
    purchase_order.db_insert()
    purchase_order.db_update_all()
    create_checkout(purchase_order.name)
    res: tuple[int, str] = get_value(
        "Checkout",
        {"purchase_order": purchase_order.name},
        ("docstatus", "purchase_order"),
    )
    assert res[0] == 1
    assert res[1] == purchase_order.name


def reverse_qtys(counter: Counter[str]):
    new_counter = counter.copy()
    for item_code in new_counter:
        new_counter[item_code] = -new_counter[item_code]
    return new_counter


@pytest.mark.parametrize("reverse_qty", (True, False, None))
def test_create_stock_entry(
    receipt_sales: Receipt, sales_order: SalesOrder, reverse_qty: bool | None
):
    receipt_sales.db_insert()
    receipt_sales.create_sales_stock_entries()

    stock_type = "Reserved Actual"
    items_obj = sales_order.get_items_with_splitted_combinations()
    items = [
        SimpleNamespace(item_code=item_code, qty=qty)
        for item_code, qty in count_qty(items_obj).items()
    ]
    create_stock_entry(
        receipt_sales.doctype,
        receipt_sales.name,
        stock_type,
        items,
        reverse_qty,  # type: ignore
    )

    entry_name: str | None = get_value(
        "Stock Entry",
        filters={
            "voucher_type": receipt_sales.doctype,
            "voucher_no": receipt_sales.name,
        },
    )
    assert entry_name is not None

    doc = get_doc(StockEntry, entry_name)
    exp_items = count_qty(items_obj)
    if reverse_qty:
        exp_items = reverse_qtys(exp_items)

    assert counters_are_same(count_qty(doc.items), exp_items)
    assert doc.docstatus == 1
    assert doc.stock_type == stock_type


def test_cancel_stock_entries_for(receipt_sales: Receipt):
    receipt_sales.insert()
    receipt_sales.submit()
    cancel_stock_entries_for(receipt_sales.doctype, receipt_sales.name)

    entries = get_all(
        StockEntry,
        field="docstatus",
        filter={
            "voucher_type": receipt_sales.doctype,
            "voucher_no": receipt_sales.name,
        },
    )
    for entry in entries:
        assert entry.docstatus == 2


@pytest.mark.parametrize(
    ("qty_sets", "expected_res"),
    (
        (((1, 4), (-10, 0), (15, 5)), {"10014030": 6, "10366598": 9}),
        (((10, 4), (-10, 0)), {"10366598": 4}),
        (((10, 4), (-10, -4)), {}),
        (((10, 4), (-20, -5)), {"10014030": -10, "10366598": -1}),
    ),
)
def test_get_stock_balance(
    receipt_sales: Receipt,
    qty_sets: tuple[tuple[int, int]],
    expected_res: dict[str, int],
):
    for first_qty, second_qty in qty_sets:
        get_doc(
            StockEntry,
            {
                "stock_type": "Available Actual",
                "voucher_type": receipt_sales.doctype,
                "voucher_no": receipt_sales.name,
                "items": [
                    {"item_code": "10014030", "qty": first_qty},
                    {"item_code": "10366598", "qty": second_qty},
                ],
            },
        ).insert()
    assert get_stock_balance("Available Actual") == expected_res
