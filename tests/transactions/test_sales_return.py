from copy import copy

import pytest

import frappe
from comfort import count_quantity, group_by_attr
from comfort.transactions.doctype.sales_order.sales_order import SalesOrder
from comfort.transactions.doctype.sales_return.sales_return import (
    SalesReturn,
    _add_rates_to_child_items,
)


def test_return_get_items_in_sales_order(
    sales_return: SalesReturn, sales_order: SalesOrder
):
    items = sales_order._get_items_with_splitted_combinations()
    _add_rates_to_child_items(items)
    return sales_return._get_items_in_sales_order() == items


def test_get_remaining_qtys(sales_return: SalesReturn):
    items_in_order = sales_return._get_items_in_sales_order()
    in_order = count_quantity(items_in_order)
    in_return = count_quantity(sales_return.items)

    for item_code, qty in sales_return._get_remaining_qtys(items_in_order):
        assert qty > 0
        if qty > 0:
            assert qty == in_order[item_code] - in_return.get(item_code, 0)


def test_get_items_available_to_add(sales_return: SalesReturn):
    available_item_and_qty = dict(
        sales_return._get_remaining_qtys(sales_return._get_items_in_sales_order())
    )
    for item in sales_return.get_items_available_to_add():
        assert (item["item_name"], item["rate"]) == frappe.get_value(
            "Item", item["item_code"], ("item_name", "rate")
        )
        assert item["qty"] == available_item_and_qty[item["item_code"]]


def test_calculate_amounts(sales_return: SalesReturn):
    sales_return.calculate_amounts()
    expected_total_amount = 0
    for item in sales_return.items:
        assert item.amount == item.qty * item.rate
        expected_total_amount += item.qty * item.rate
    assert sales_return.total_amount == expected_total_amount


@pytest.mark.parametrize(
    ("item_code", "qty"),
    (
        ("invalid_item_code", 10),
        ("40366634", 0),
        ("40366634", 3),
        #  ("", 1000)
    ),
)
def test_add_items_raises_on_invalid_item(
    sales_return: SalesReturn, item_code: str, qty: int
):
    all_items = sales_return.get_items_available_to_add()
    counter = count_quantity(frappe._dict(d) for d in all_items)

    with pytest.raises(
        frappe.ValidationError,
        match=f"Insufficient quantity {qty} for Item {item_code}: expected not "
        + f"more than {counter.get(item_code, 0)}.",
    ):
        sales_return.add_items(
            [
                {
                    "item_code": item_code,
                    "item_name": "random_name",
                    "qty": qty,
                    "rate": 1000,
                }
            ]
        )


def test_add_items(sales_return: SalesReturn):
    total_amount_before = copy(sales_return.total_amount)
    expected_item_amount = 2000
    test_item = {
        "item_code": "40366634",
        "item_name": "random_name",
        "qty": 2,
        "rate": 1000,
    }
    sales_return.add_items([test_item])

    item_added, item_amount = False, 0
    for item in sales_return.items:
        if {
            "item_code": item.item_code,
            "item_name": item.item_name,
            "qty": item.qty,
            "rate": item.rate,
        } == test_item:
            item_added = True
            item_amount = item.amount

    assert item_added
    assert item_amount == expected_item_amount
    assert total_amount_before != sales_return.total_amount


@pytest.mark.usefixtures("sales_return")
def test_add_rates_to_child_items(sales_order: SalesOrder):
    grouped_order_items = group_by_attr(sales_order.items, attr="name")
    items = sales_order._get_items_with_splitted_combinations()
    _add_rates_to_child_items(items)

    for item in items:
        if item.doctype == "Sales Order Item":
            assert item.rate == grouped_order_items[item.name][0].rate
        elif item.doctype == "Sales Order Child Item":
            assert item.rate == frappe.get_value("Item", item.item_code, "rate")
