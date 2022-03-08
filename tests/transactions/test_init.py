from __future__ import annotations

from collections import Counter
from types import SimpleNamespace

import pytest

import frappe
from comfort.transactions import PurchaseReturn, SalesOrder, SalesReturn
from comfort.transactions.return_ import _ReturnAddItemsPayloadItem
from comfort.transactions.utils import delete_empty_items, merge_same_items
from comfort.utils import count_qty, get_value, group_by_attr


def test_return_delete_empty_items(sales_return: SalesReturn):
    sales_return.append("items", {"qty": 0})
    sales_return.delete_empty_items()
    c: Counter[str] = Counter()
    for i in sales_return.items:
        c[i.item_code] += i.qty
    for qty in c.values():
        assert qty > 0


def test_return_delete_empty_items_no_attr(sales_return: SalesReturn):
    del sales_return.items
    sales_return.delete_empty_items()


def test_return_delete_empty_items_attr_is_none(sales_return: SalesReturn):
    sales_return.items = None  # type: ignore
    sales_return.delete_empty_items()


def test_return_calculate_item_values(sales_return: SalesReturn):
    sales_return._calculate_item_values()
    for item in sales_return.items:
        assert item.amount == item.qty * item.rate


def test_return_get_remaining_qtys(sales_return: SalesReturn):
    items_in_order = sales_return._voucher.get_items_with_splitted_combinations()
    in_order = count_qty(items_in_order)
    in_return = count_qty(sales_return.items)

    for item_code, qty in sales_return._get_remaining_qtys(items_in_order):
        assert qty > 0
        if qty > 0:
            assert qty == in_order[item_code] - in_return.get(item_code, 0)


def test_return_add_missing_fields_to_items(
    sales_return: SalesReturn, sales_order: SalesOrder
):
    grouped_order_items = group_by_attr(sales_order.items, attr="name")
    items = sales_order.get_items_with_splitted_combinations()
    sales_return._add_missing_fields_to_items(items)

    for item in items:
        if item.doctype == "Sales Order Item":
            assert item.rate == grouped_order_items[item.name][0].rate  # type: ignore
        elif item.doctype == "Sales Order Child Item":
            assert item.rate == get_value("Item", item.item_code, "rate")  # type: ignore


def test_return_get_items_available_to_add(sales_return: SalesReturn):
    available_item_and_qty: dict[str, int] = dict(
        sales_return._get_remaining_qtys(
            sales_return._voucher.get_items_with_splitted_combinations()
        )
    )
    for item in sales_return.get_items_available_to_add():
        assert (item["item_name"], item["rate"]) == get_value(
            "Item", item["item_code"], ("item_name", "rate")
        )
        assert item["qty"] == available_item_and_qty[item["item_code"]]


@pytest.mark.parametrize(
    ("item_code", "qty"),
    (("invalid_item_code", 10), ("40366634", 0), ("40366634", 3)),
)
def test_return_validate_new_item(sales_return: SalesReturn, item_code: str, qty: int):
    all_items = sales_return.get_items_available_to_add()
    counter = count_qty(SimpleNamespace(**i) for i in all_items)

    with pytest.raises(
        frappe.ValidationError,
        match=f"Insufficient quantity {qty} for Item {item_code}: expected not "
        + f"more than {counter.get(item_code, 0)}.",
    ):
        sales_return._validate_new_item(
            counter,
            {
                "item_code": item_code,
                "item_name": "random_name",
                "qty": qty,
                "rate": 1000,
            },
        )


def test_return_add_items(sales_return: SalesReturn):
    expected_item_amount = 2000
    test_item: _ReturnAddItemsPayloadItem = {
        "item_code": "40366634",
        "item_name": "random_name",
        "qty": 2,
        "rate": 1000,
    }
    sales_return.add_items([test_item])

    item_added, item_amount = False, 0
    for item in sales_return.items:
        if (
            _ReturnAddItemsPayloadItem(
                item_code=item.item_code,
                item_name=item.item_name,
                qty=item.qty,
                rate=item.rate,
            )
            == test_item
        ):
            item_added = True
            item_amount = item.amount

    assert item_added
    assert item_amount == expected_item_amount


def test_return_validate_not_all_items_returned_not_raises(
    purchase_return: PurchaseReturn,
):
    purchase_return._validate_not_all_items_returned()


def test_return_validate_not_all_items_returned_raises(purchase_return: PurchaseReturn):
    purchase_return.add_items(purchase_return.get_items_available_to_add())
    with pytest.raises(frappe.ValidationError, match="Can't return all items"):
        purchase_return._validate_not_all_items_returned()


def test_delete_empty_items(sales_order: SalesOrder):
    sales_order.append("items", {"qty": 0})
    delete_empty_items(sales_order, "items")
    c: Counter[str] = Counter()
    for i in sales_order.items:
        c[i.item_code] += i.qty

    for qty in c.values():
        assert qty > 0


def test_merge_same_items(sales_order: SalesOrder):
    item = sales_order.items[0].as_dict().copy()
    item.qty = 4
    second_item = sales_order.items[1].as_dict().copy()
    second_item.qty = 2
    sales_order.extend("items", [item, second_item])

    sales_order.items = merge_same_items(sales_order.items)
    c: Counter[str] = Counter()
    for item in sales_order.items:
        c[item.item_code] += 1

    assert len(sales_order.items) == 2
    assert all(c == 1 for c in c.values())
