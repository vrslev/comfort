from __future__ import annotations

from collections import Counter
from types import SimpleNamespace

import pytest

import frappe
from comfort import count_qty, counters_are_same, get_doc, new_doc
from comfort.stock.doctype.waiting_list.waiting_list import WaitingList
from comfort.transactions.doctype.purchase_order.purchase_order import PurchaseOrder
from comfort.transactions.doctype.sales_order.sales_order import SalesOrder
from comfort.transactions.doctype.sales_order_child_item.sales_order_child_item import (
    SalesOrderChildItem,
)
from comfort.transactions.doctype.sales_order_item.sales_order_item import (
    SalesOrderItem,
)
from tests.conftest import mock_delivery_services


@pytest.fixture
def waiting_list(sales_order: SalesOrder):
    sales_order.insert()
    new_sales_order = new_doc(SalesOrder)  # type: ignore
    new_sales_order.customer = sales_order.customer
    new_sales_order.append(
        "items", {"item_code": sales_order.items[0].item_code, "qty": 2}
    )
    new_sales_order.insert()

    return get_doc(
        WaitingList,
        {
            "sales_orders": [
                {"sales_order": sales_order.name},
                {"sales_order": new_sales_order.name},
            ]
        },
    )


def test_waiting_list_get_items(waiting_list: WaitingList):
    items = waiting_list._get_items()
    exp_items: list[SalesOrderChildItem | SalesOrderItem] = []
    for order in waiting_list.sales_orders:
        doc = get_doc(SalesOrder, order.sales_order)
        exp_items += doc.get_items_with_splitted_combinations()
    assert counters_are_same(count_qty(items), count_qty(exp_items))


def test_get_unavailable_items_counter(waiting_list: WaitingList):
    items = [
        SimpleNamespace(item_code="50366596", qty=1),
        SimpleNamespace(item_code="10366598", qty=2),
        SimpleNamespace(item_code="11111111", qty=3),
    ]
    unavailable_items = mock_delivery_services.delivery_options[0].unavailable_items
    cannot_add_items = ["11111111"]
    counter = waiting_list._get_unavailable_items_counter(
        items,  # type: ignore
        unavailable_items,
        cannot_add_items,
    )
    assert counters_are_same(
        counter, Counter({"50366596": 0, "10366598": 0, "11111111": 0})
    )


@pytest.mark.parametrize(
    ("items_counter", "unavailable_items_counter", "is_available", "exp_status"),
    (
        ({"50366596": 1}, {"50366596": 0}, True, "Not Available"),
        ({"50366596": 1}, {}, False, "Not Available"),
        ({"50366596": 1, "50366595": 1}, {"50366596": 0}, True, "Partially Available"),
        ({"50366596": 1, "50366595": 1}, {}, True, "Fully Available"),
        ({"50366596": 1, "50366595": 1}, {"50366596": 1}, True, "Fully Available"),
    ),
)
def test_get_status_for_order(
    waiting_list: WaitingList,
    items_counter: dict[str, int],
    unavailable_items_counter: dict[str, int],
    is_available: bool,
    exp_status: str,
):
    items = [
        SimpleNamespace(item_code=item_code, qty=qty)
        for item_code, qty in items_counter.items()
    ]
    assert (
        waiting_list._get_status_for_order(
            items=items,  # type: ignore
            unavailable_items_counter=Counter(unavailable_items_counter),
            is_available=is_available,
        )
        == exp_status
    )


def test_show_already_in_po_message_in_po(
    waiting_list: WaitingList, purchase_order: PurchaseOrder
):
    purchase_order.insert()
    waiting_list.sales_orders.pop(0)
    waiting_list.append(
        "sales_orders", {"sales_order": purchase_order.sales_orders[0].sales_order_name}
    )
    frappe.message_log = []
    waiting_list._show_already_in_po_message()
    assert (
        f"Sales Orders already in Purchase Order: {waiting_list.sales_orders[1].sales_order}"
        in str(frappe.message_log)  # type: ignore
    )


def test_show_already_in_po_message_not_in_po(waiting_list: WaitingList):
    frappe.message_log = []
    waiting_list._show_already_in_po_message()
    assert frappe.message_log == []
