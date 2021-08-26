from __future__ import annotations

import json
from typing import Any, Callable

import ikea_api_wrapped
import pytest

import frappe
from comfort import count_quantity, group_by_key
from comfort.entities.doctype.child_item.child_item import ChildItem
from comfort.stock.doctype.stock_entry.stock_entry import StockEntry
from comfort.transactions.doctype.purchase_order.purchase_order import PurchaseOrder
from comfort.transactions.doctype.sales_order_child_item.sales_order_child_item import (
    SalesOrderChildItem,
)
from comfort.transactions.doctype.sales_order_item.sales_order_item import (
    SalesOrderItem,
)
from frappe import ValidationError
from frappe.utils.data import add_to_date, getdate, now_datetime, today
from tests.conftest import mock_delivery_services, mock_purchase_info

#############################
#   PurchaseOrderMethods    #
#############################


def test_validate_not_empty(purchase_order: PurchaseOrder):
    purchase_order.sales_orders = purchase_order.items_to_sell = []
    with pytest.raises(ValidationError, match="Add Sales Orders or Items to Sell"):
        purchase_order.validate_not_empty()


def test_delete_sales_order_dublicates(purchase_order: PurchaseOrder):
    purchase_order.sales_orders = [
        purchase_order.sales_orders[0],
        purchase_order.sales_orders[0],
    ]
    purchase_order.delete_sales_order_dublicates()

    for orders in group_by_key(
        purchase_order.sales_orders, key="sales_order_name"
    ).values():
        assert len(orders) == 1


def test_update_sales_orders_from_db(purchase_order: PurchaseOrder):
    for order in purchase_order.sales_orders:
        order.customer = order.total = None

    purchase_order.update_sales_orders_from_db()
    for order in purchase_order.sales_orders:
        customer, total = frappe.get_value(
            "Sales Order", order.sales_order_name, ("customer", "total_amount")
        )
        customer: str
        total: int
        assert order.customer == customer
        assert order.total == total


def test_update_items_to_sell_from_db(purchase_order: PurchaseOrder):
    for i in purchase_order.items_to_sell:
        i.item_name = i.rate = i.amount = i.weight = None

    purchase_order.update_items_to_sell_from_db()
    for i in purchase_order.items_to_sell:
        item_values: tuple[str, int, float] = frappe.get_value(
            "Item", i.item_code, ("item_name", "rate", "weight")
        )
        item_name, rate, weight = item_values
        assert i.item_name == item_name
        assert i.rate == rate
        assert i.weight == weight
        assert i.amount == rate * i.qty


def test_calculate_items_to_sell_cost(purchase_order: PurchaseOrder):
    purchase_order.update_items_to_sell_from_db()
    purchase_order._calculate_items_to_sell_cost()
    assert purchase_order.items_to_sell_cost == sum(
        i.amount for i in purchase_order.items_to_sell
    )


def test_calculate_items_to_sell_cost_if_no_items_to_sell(
    purchase_order: PurchaseOrder,
):
    purchase_order.items_to_sell = []
    purchase_order.update_items_to_sell_from_db()
    purchase_order._calculate_items_to_sell_cost()
    assert purchase_order.items_to_sell_cost == 0


def test_calculate_sales_orders_cost(purchase_order: PurchaseOrder):
    purchase_order._calculate_sales_orders_cost()
    res: list[int] = frappe.get_all(
        "Sales Order Item",
        fields="SUM(qty * rate) AS sales_orders_cost",
        filters={
            "parent": (
                "in",
                (ord.sales_order_name for ord in purchase_order.sales_orders),
            )
        },
        as_list=True,
    )
    assert purchase_order.sales_orders_cost == res[0][0]


def test_calculate_sales_orders_cost_if_no_sales_orders(purchase_order: PurchaseOrder):
    purchase_order.sales_orders = []
    purchase_order._calculate_sales_orders_cost()
    assert purchase_order.sales_orders_cost == 0


@pytest.mark.parametrize(
    "updated_items_to_sell,updated_sales_orders",
    (
        (None, None),
        ([], None),
        (None, []),
        ([], []),
    ),
)
def test_calculate_total_weight(
    purchase_order: PurchaseOrder,
    updated_items_to_sell: list[Any] | None,
    updated_sales_orders: list[Any] | None,
):
    if updated_items_to_sell is not None:
        purchase_order.items_to_sell = updated_items_to_sell
    if updated_sales_orders is not None:
        purchase_order.sales_orders = updated_sales_orders

    purchase_order.update_items_to_sell_from_db()
    purchase_order._calculate_total_weight()

    res: list[float] = frappe.get_all(
        "Sales Order Item",
        fields="SUM(total_weight) AS total_weight",
        filters={
            "parent": (
                "in",
                (ord.sales_order_name for ord in purchase_order.sales_orders),
            )
        },
        as_list=True,
    )
    exp_total_weight = res[0][0] or 0 + sum(
        i.weight * i.qty for i in purchase_order.items_to_sell
    )
    assert purchase_order.total_weight == exp_total_weight


def test_calculate_total_amount_costs_set_if_none(
    purchase_order: PurchaseOrder,
):
    purchase_order.delivery_cost = None
    purchase_order.items_to_sell_cost = None
    purchase_order.sales_orders_cost = None
    purchase_order._calculate_total_amount()
    assert purchase_order.delivery_cost == 0
    assert purchase_order.items_to_sell_cost == 0
    assert purchase_order.sales_orders_cost == 0


def test_calculate_total_amount(purchase_order: PurchaseOrder):
    delivery_cost = 5399
    items_to_sell_cost = 1940
    sales_orders_cost = 21030
    purchase_order.delivery_cost = delivery_cost
    purchase_order.items_to_sell_cost = items_to_sell_cost
    purchase_order.sales_orders_cost = sales_orders_cost

    purchase_order._calculate_total_amount()
    assert purchase_order.total_amount == (
        delivery_cost + items_to_sell_cost + sales_orders_cost
    )


def test_get_items_to_sell_with_empty_items_to_sell(purchase_order: PurchaseOrder):
    purchase_order.items_to_sell = []
    items = purchase_order._get_items_to_sell(split_combinations=False)
    assert items == []


def test_get_items_to_sell_no_split_combinations(purchase_order: PurchaseOrder):
    items = purchase_order._get_items_to_sell(split_combinations=False)
    assert items == purchase_order.items_to_sell


def test_get_items_to_sell_split_combinations(purchase_order: PurchaseOrder):
    items = purchase_order._get_items_to_sell(split_combinations=True)

    child_items: list[ChildItem] = frappe.get_all(
        "Child Item",
        fields=("parent", "item_code", "qty"),
        filters={"parent": ("in", (i.item_code for i in purchase_order.items_to_sell))},
    )
    parents = (child.parent for child in child_items)
    items_to_sell = [
        i for i in purchase_order.items_to_sell.copy() if i.item_code not in parents
    ]

    assert items == items_to_sell + child_items


def test_get_items_in_sales_orders_with_empty_sales_orders(
    purchase_order: PurchaseOrder,
):
    purchase_order.sales_orders = []
    items = purchase_order._get_items_in_sales_orders(split_combinations=False)
    assert items == []


def test_get_items_in_sales_orders_no_split_combinations(purchase_order: PurchaseOrder):
    exp_items: list[SalesOrderItem] = frappe.get_all(
        "Sales Order Item",
        fields=("item_code", "qty"),
        filters={
            "parent": (
                "in",
                (ord.sales_order_name for ord in purchase_order.sales_orders),
            )
        },
    )
    items = purchase_order._get_items_in_sales_orders(split_combinations=False)
    assert items == exp_items


def test_get_items_in_sales_orders_split_combinations(purchase_order: PurchaseOrder):
    sales_order_names = (ord.sales_order_name for ord in purchase_order.sales_orders)
    so_items: list[SalesOrderItem] = frappe.get_all(
        "Sales Order Item",
        fields=("item_code", "qty"),
        filters={"parent": ("in", sales_order_names)},
    )
    child_items: list[SalesOrderChildItem] = frappe.get_all(
        "Sales Order Child Item",
        fields=("parent_item_code", "item_code", "qty"),
        filters={"parent": ("in", sales_order_names)},
    )
    parents = (i.parent_item_code for i in child_items)
    exp_items = child_items + [i for i in so_items if i.item_code not in parents]
    items = purchase_order._get_items_in_sales_orders(split_combinations=True)
    assert items == exp_items


@pytest.mark.parametrize("split_combinations", (True, False))
def test_get_templated_items_for_api(
    purchase_order: PurchaseOrder, split_combinations: bool
):
    items_for_api = purchase_order._get_templated_items_for_api(split_combinations)
    assert (
        count_quantity(
            purchase_order._get_items_to_sell(split_combinations)  # type: ignore
            + purchase_order._get_items_in_sales_orders(split_combinations)
        )
        == items_for_api
    )


@pytest.mark.usefixtures("ikea_settings")
def test_get_delivery_services(purchase_order: PurchaseOrder):
    purchase_order.get_delivery_services()
    assert purchase_order.cannot_add_items == json.dumps(
        mock_delivery_services["cannot_add"]
    )
    assert len(purchase_order.delivery_options) == len(
        mock_delivery_services["delivery_options"]
    )


@pytest.mark.usefixtures("ikea_settings")
def test_get_delivery_services_no_response(
    purchase_order: PurchaseOrder, monkeypatch: pytest.MonkeyPatch
):
    mock_func: Callable[[Any, Any, Any], None] = lambda api, items, zip_code: None
    monkeypatch.setattr(ikea_api_wrapped, "get_delivery_services", mock_func)
    purchase_order.get_delivery_services()
    assert not purchase_order.cannot_add_items
    assert not purchase_order.delivery_options


def test_create_stock_entries_for_purchased(purchase_order: PurchaseOrder):
    purchase_order.db_insert()
    purchase_order.db_update_all()
    purchase_order.create_stock_entries_for_purchased()

    entry_names: list[StockEntry] = frappe.get_all(
        "Stock Entry",
        filters={
            "voucher_type": purchase_order.doctype,
            "voucher_no": purchase_order.name,
        },
    )

    for name in entry_names:
        doc: StockEntry = frappe.get_doc("Stock Entry", name)
        assert doc.stock_type in ("Reserved Purchased", "Available Purchased")
        if doc.stock_type == "Reserved Purchased":
            exp_items = count_quantity(purchase_order._get_items_in_sales_orders(True))
            for i in count_quantity(doc.items):
                assert i in exp_items

        elif doc.stock_type == "Available Purchased":
            exp_items = count_quantity(purchase_order._get_items_to_sell(True))
            for i in count_quantity(doc.items):
                assert i in exp_items


def test_create_payment(purchase_order: PurchaseOrder):
    amount = 5000
    purchase_order.total_amount = amount
    purchase_order.db_insert()
    purchase_order.create_payment()

    res: tuple[int, bool] = frappe.get_value(
        "Payment",
        fieldname=["amount", "paid_with_cash"],
        filters={
            "voucher_type": purchase_order.doctype,
            "voucher_no": purchase_order.name,
        },
    )
    assert res[0] == amount
    assert res[1]


#############################
#       PurchaseOrder       #
#############################


def get_this_month_ru_name():
    months_number_to_name = {
        1: "Январь",
        2: "Февраль",
        3: "Март",
        4: "Апрель",
        5: "Май",
        6: "Июнь",
        7: "Июль",
        8: "Август",
        9: "Сентябрь",
        10: "Октябрь",
        11: "Ноябрь",
        12: "Декабрь",
    }

    return months_number_to_name[now_datetime().month]


def test_autoname_purchase_orders_exist_in_this_month(purchase_order: PurchaseOrder):
    this_month = get_this_month_ru_name()
    frappe.get_doc({"doctype": "Purchase Order", "name": f"{this_month}-1"}).db_insert()
    purchase_order.autoname()
    assert purchase_order.name == f"{this_month}-2"


def test_autoname_purchase_orders_not_exist_in_this_month(
    purchase_order: PurchaseOrder,
):
    purchase_order.autoname()
    assert purchase_order.name == f"{get_this_month_ru_name()}-1"


def test_before_save(purchase_order: PurchaseOrder):
    purchase_order.delivery_options.append("somevalue")
    purchase_order.before_save()
    assert len(purchase_order.delivery_options) == 0


def test_before_insert(purchase_order: PurchaseOrder):
    purchase_order.status = None
    purchase_order.before_insert()
    assert purchase_order.status == "Draft"


def test_before_submit(purchase_order: PurchaseOrder):
    purchase_order.status = "Draft"
    purchase_order.get_delivery_services()
    purchase_order.before_submit()

    assert not purchase_order.delivery_options
    assert not purchase_order.cannot_add_items
    assert purchase_order.status == "To Receive"


def test_add_purchase_info_and_submit_info_loaded(purchase_order: PurchaseOrder):
    purchase_order.db_insert()
    purchase_id = "111111110"
    purchase_order.add_purchase_info_and_submit(
        purchase_id, purchase_info_loaded=True, purchase_info=mock_purchase_info
    )
    assert purchase_order.schedule_date == getdate(mock_purchase_info["delivery_date"])
    assert purchase_order.posting_date == getdate(mock_purchase_info["purchase_date"])
    assert purchase_order.delivery_cost == mock_purchase_info["delivery_cost"]
    assert purchase_order.order_confirmation_no == purchase_id
    assert purchase_order.docstatus == 1


def test_add_purchase_info_and_submit_info_not_loaded(purchase_order: PurchaseOrder):
    purchase_id, delivery_cost = "111111110", 2199
    purchase_order.db_insert()
    purchase_order.add_purchase_info_and_submit(
        purchase_id,
        purchase_info_loaded=False,
        purchase_info={},
        delivery_cost=delivery_cost,
    )
    assert purchase_order.schedule_date.date() == add_to_date(None, weeks=2).date()
    assert purchase_order.posting_date == today()
    assert purchase_order.delivery_cost == delivery_cost
    assert purchase_order.order_confirmation_no == purchase_id
    assert purchase_order.docstatus == 1


def test_get_unavailable_items_in_cart_by_orders(
    purchase_order: PurchaseOrder,
):  # TODO: Test business logic
    unavailable_items = [
        {"item_code": "50366596", "available_qty": 0},
        {"item_code": "10366598", "available_qty": 0},
        {"item_code": "29128569", "available_qty": 0},
    ]

    res = purchase_order.get_unavailable_items_in_cart_by_orders(
        unavailable_items,
    )

    acceptable_parents = [s.sales_order_name for s in purchase_order.sales_orders]
    acceptable_parents.append(purchase_order.name)

    grouped_items = group_by_key(frappe._dict(i) for i in res)

    for items in grouped_items.values():
        for idx, item in enumerate(items):
            assert item.item_name == frappe.get_value(
                "Item", item.item_code, "item_name"
            )
            assert item.parent in acceptable_parents

            if idx == 0:
                assert item.available_qty is not None
            else:
                assert item.available_qty is None
