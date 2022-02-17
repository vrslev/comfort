from __future__ import annotations

import json
from copy import copy, deepcopy
from datetime import datetime
from typing import Any

import ikea_api.wrappers
import pytest
from ikea_api.wrappers.types import GetDeliveryServicesResponse

import comfort.transactions.doctype.purchase_order.purchase_order
import frappe
from comfort import (
    count_qty,
    counters_are_same,
    get_all,
    get_doc,
    get_value,
    group_by_attr,
    new_doc,
)
from comfort.entities.doctype.item.item import Item
from comfort.integrations.ikea import FetchItemsResult, PurchaseInfoDict
from comfort.transactions import AnyChildItem
from comfort.transactions.doctype.purchase_order.purchase_order import (
    PurchaseOrder,
    calculate_total_weight_and_total_weight,
)
from comfort.transactions.doctype.sales_order.sales_order import SalesOrder
from comfort.transactions.doctype.sales_order_child_item.sales_order_child_item import (
    SalesOrderChildItem,
)
from comfort.transactions.doctype.sales_order_item.sales_order_item import (
    SalesOrderItem,
)
from frappe import ValidationError
from frappe.utils.data import getdate, now_datetime, today
from tests.conftest import mock_delivery_services, mock_purchase_info


def test_validate_not_empty(purchase_order: PurchaseOrder):
    purchase_order.sales_orders = purchase_order.items_to_sell = []
    with pytest.raises(ValidationError, match="Add Sales Orders or Items to Sell"):
        purchase_order._validate_not_empty()


def test_delete_sales_order_duplicates(purchase_order: PurchaseOrder):
    purchase_order.sales_orders = [
        purchase_order.sales_orders[0],
        purchase_order.sales_orders[0],
    ]
    purchase_order._delete_sales_order_duplicates()

    for orders in group_by_attr(
        purchase_order.sales_orders, "sales_order_name"
    ).values():
        assert len(orders) == 1


def test_update_sales_orders_from_db_not_none(purchase_order: PurchaseOrder):
    for order in purchase_order.sales_orders:
        order.customer = order.total_amount = None  # type: ignore

    purchase_order.update_sales_orders_from_db()
    for order in purchase_order.sales_orders:
        values: tuple[str, int] = get_value(
            "Sales Order", order.sales_order_name, ("customer", "total_amount")
        )
        customer, total_amount = values
        assert order.customer == customer
        assert order.total_amount == total_amount


def test_update_sales_orders_from_db_is_none():
    purchase_order = new_doc(PurchaseOrder)
    purchase_order.append(
        "sales_orders",
        {"sales_order_name": "some name", "customer": None, "total_amount": None},
    )
    purchase_order.update_sales_orders_from_db()
    assert purchase_order.sales_orders[0].customer is None
    assert purchase_order.sales_orders[0].total_amount is None


def test_update_items_to_sell_from_db(purchase_order: PurchaseOrder):
    for i in purchase_order.items_to_sell:
        i.item_name = i.rate = i.amount = i.weight = None  # type: ignore

    purchase_order.update_items_to_sell_from_db()
    for i in purchase_order.items_to_sell:
        item_values: tuple[str, int, float] = get_value(
            "Item", i.item_code, ("item_name", "rate", "weight")
        )
        item_name, rate, weight = item_values
        assert i.item_name == item_name
        assert i.rate == rate
        assert i.weight == weight
        assert i.amount == rate * i.qty


def test_clear_no_copy_fields_for_amended_true(purchase_order: PurchaseOrder):
    purchase_order.amended_from = "Октябрь-1"
    purchase_order._clear_no_copy_fields_for_amended()
    assert purchase_order.posting_date is None
    assert purchase_order.order_confirmation_no is None
    assert purchase_order.schedule_date is None
    assert purchase_order.delivery_cost == 0


def test_clear_no_copy_fields_for_amended_false(purchase_order: PurchaseOrder):
    mydate = datetime.now()
    order_confirmation_no = "111111111"
    delivery_cost = 1000
    purchase_order.amended_from = None
    purchase_order.posting_date = copy(mydate)
    purchase_order.order_confirmation_no = copy(order_confirmation_no)
    purchase_order.schedule_date = copy(mydate)
    purchase_order.delivery_cost = copy(delivery_cost)
    purchase_order._clear_no_copy_fields_for_amended()
    assert purchase_order.posting_date == mydate
    assert purchase_order.order_confirmation_no == order_confirmation_no
    assert purchase_order.schedule_date == mydate
    assert purchase_order.delivery_cost == delivery_cost


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
    doc = get_doc(
        SalesOrderItem,
        {
            "parent": purchase_order.sales_orders[0].sales_order_name,
            "parenttype": "Sales Order",
            "item_code": "Some Item Code",
            "qty": 1,
            "rate": 100,
        },
    )
    doc.flags.ignore_links = True
    doc.insert()
    doc.db_set("docstatus", 2)

    res: list[list[int]] = frappe.get_all(
        "Sales Order Item",
        fields="SUM(qty * rate) AS sales_orders_cost",
        filters={
            "parent": (
                "in",
                (o.sales_order_name for o in purchase_order.sales_orders),
            ),
            "docstatus": ("!=", 2),
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
def test_calculate_total_weight_main(
    purchase_order: PurchaseOrder,
    updated_items_to_sell: list[Any] | None,
    updated_sales_orders: list[Any] | None,
):
    if updated_items_to_sell is not None:
        purchase_order.items_to_sell = updated_items_to_sell
    if updated_sales_orders is not None:
        purchase_order.sales_orders = updated_sales_orders

    if updated_sales_orders:
        cancelled_item = new_doc(SalesOrderItem)
        cancelled_item.total_weight = 100000
        cancelled_item.docstatus = 2
        cancelled_item.parent = purchase_order.sales_orders[0].sales_order_name
        cancelled_item.db_update()

    purchase_order.update_items_to_sell_from_db()
    purchase_order._calculate_total_weight()

    res: list[list[float]] = frappe.get_all(
        "Sales Order Item",
        fields="SUM(total_weight) AS total_weight",
        filters={
            "parent": ("in", (o.sales_order_name for o in purchase_order.sales_orders)),
            "docstatus": ("!=", 2),
        },
        as_list=True,
    )
    exp_total_weight = res[0][0] or 0 + sum(
        i.weight * i.qty for i in purchase_order.items_to_sell
    )
    assert purchase_order.total_weight == exp_total_weight


@pytest.mark.parametrize(("qty", "weight"), ((None, 10), (10, None), (None, None)))
def test_calculate_total_weight_empty_item(
    purchase_order: PurchaseOrder, qty: int | None, weight: int | None
):
    item = purchase_order.items_to_sell[0]
    item.qty = qty  # type: ignore
    item.weight = weight  # type: ignore
    purchase_order._calculate_total_weight()


def test_calculate_total_amount_costs_set_if_none(
    purchase_order: PurchaseOrder,
):
    purchase_order.delivery_cost = None  # type: ignore
    purchase_order.items_to_sell_cost = None  # type: ignore
    purchase_order.sales_orders_cost = None  # type: ignore
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


def test_calculate_total_margin_no_sales_order(purchase_order: PurchaseOrder):
    purchase_order._calculate_total_margin()
    assert purchase_order.total_margin == 0


def test_calculate_total_margin_with_sales_order(purchase_order: PurchaseOrder):
    cancelled_order = get_doc(SalesOrder, {"name": "test"})
    cancelled_order.margin = 200
    cancelled_order.docstatus = 2
    cancelled_order.db_insert()
    purchase_order.append("sales_orders", {"sales_order_name": cancelled_order.name})

    purchase_order._calculate_total_margin()
    assert (
        purchase_order.total_margin
        == get_all(
            SalesOrder,
            filter={"name": purchase_order.sales_orders[0].sales_order_name},
            field="SUM(margin) as margin",
        )[0].margin
    )


def test_get_items_to_sell_with_empty_items_to_sell(purchase_order: PurchaseOrder):
    purchase_order.items_to_sell = []
    items = purchase_order.get_items_to_sell(split_combinations=False)
    assert items == []


def test_get_items_to_sell_no_split_combinations(purchase_order: PurchaseOrder):
    items = purchase_order.get_items_to_sell(split_combinations=False)
    assert items == purchase_order.items_to_sell


def test_get_items_to_sell_split_combinations(
    purchase_order: PurchaseOrder, item: Item
):
    item_without_children = item.child_items[0]
    purchase_order.append(
        "items_to_sell",
        {
            "item_code": item_without_children.item_code,
            "qty": 5,
        },
    )

    items = purchase_order.get_items_to_sell(split_combinations=True)

    exp_counter = count_qty(item.child_items)
    for key in exp_counter:
        exp_counter[key] = exp_counter[key] * 2
    exp_counter[item_without_children.item_code] += 5

    assert counters_are_same(count_qty(items), exp_counter)
    # child_items = get_all(
    #     ChildItem,
    #     fields=("parent", "item_code", "qty"),
    #     filters={"parent": ("in", (i.item_code for i in purchase_order.items_to_sell))},
    # )
    # count_qty(item.child_items)
    # parents = (child.parent for child in child_items)
    # items_to_sell = [
    #     i for i in purchase_order.items_to_sell.copy() if i.item_code not in parents
    # ]
    # exp_list: list[PurchaseOrderItemToSell | ChildItem] = list(items_to_sell)
    # exp_list += child_items
    # assert items == exp_list


def test_get_items_in_sales_orders_with_empty_sales_orders(
    purchase_order: PurchaseOrder,
):
    purchase_order.sales_orders = []
    items = purchase_order.get_items_in_sales_orders(split_combinations=False)
    assert items == []


def test_get_items_in_sales_orders_with_cancelled_items(
    purchase_order: PurchaseOrder, item: Item
):
    doc = new_doc(SalesOrder)
    doc.__newname = "test1"  # type: ignore
    doc.customer = purchase_order.sales_orders[0].customer
    doc.append("items", {"item_code": item.item_code, "qty": 1})
    doc.submit()
    doc.cancel()

    purchase_order.sales_orders = []
    purchase_order.append("sales_orders", {"sales_order_name": doc.name})
    items = purchase_order.get_items_in_sales_orders(split_combinations=False)
    assert items == []


def test_get_items_in_sales_orders_no_split_combinations(purchase_order: PurchaseOrder):
    exp_items = get_all(
        SalesOrderItem,
        field=("item_code", "qty"),
        filter={
            "parent": (
                "in",
                (o.sales_order_name for o in purchase_order.sales_orders),
            )
        },
    )
    items = purchase_order.get_items_in_sales_orders(split_combinations=False)
    assert items == exp_items


def test_get_items_in_sales_orders_split_combinations(purchase_order: PurchaseOrder):
    sales_order_names = [o.sales_order_name for o in purchase_order.sales_orders]
    so_items = get_all(
        SalesOrderItem,
        field=("item_code", "qty"),
        filter={"parent": ("in", sales_order_names)},
    )
    child_items = get_all(
        SalesOrderChildItem,
        field=("parent_item_code", "item_code", "qty"),
        filter={"parent": ("in", sales_order_names)},
    )
    parents = [i.parent_item_code for i in child_items]
    exp_items: list[SalesOrderItem | SalesOrderChildItem] = list(child_items)
    exp_items += [i for i in so_items if i.item_code not in parents]
    items = purchase_order.get_items_in_sales_orders(split_combinations=True)
    assert items == exp_items


@pytest.mark.parametrize("split_combinations", (True, False))
def test_get_templated_items_for_api(
    purchase_order: PurchaseOrder, split_combinations: bool
):
    items_for_api = purchase_order._get_templated_items_for_api(split_combinations)
    all_items: list[AnyChildItem] = list(
        purchase_order.get_items_to_sell(split_combinations)
    )
    all_items += purchase_order.get_items_in_sales_orders(split_combinations)
    assert count_qty(all_items) == items_for_api


@pytest.mark.usefixtures("ikea_settings")
def test_get_delivery_services_with_response(purchase_order: PurchaseOrder):
    purchase_order.db_insert()
    purchase_order.get_delivery_services()
    assert purchase_order.cannot_add_items == json.dumps(
        mock_delivery_services.cannot_add
    )
    assert len(purchase_order.delivery_options) == len(
        mock_delivery_services.delivery_options
    )


@pytest.mark.usefixtures("ikea_settings")
def test_get_delivery_services_no_response(
    purchase_order: PurchaseOrder, monkeypatch: pytest.MonkeyPatch
):
    def mock_get_delivery_services(api: Any, *, items: Any, zip_code: Any):
        return GetDeliveryServicesResponse(delivery_options=[], cannot_add=[])

    monkeypatch.setattr(
        ikea_api.wrappers, "get_delivery_services", mock_get_delivery_services
    )

    purchase_order.get_delivery_services()
    assert not purchase_order.cannot_add_items
    assert not purchase_order.delivery_options


def test_create_payment(purchase_order: PurchaseOrder):
    amount = 5000
    purchase_order.total_amount = amount
    purchase_order.db_insert()
    purchase_order._create_payment()

    res: tuple[int, bool] = get_value(
        "Payment",
        fieldname=("amount", "paid_with_cash"),
        filters={
            "voucher_type": purchase_order.doctype,
            "voucher_no": purchase_order.name,
        },
    )
    assert res[0] == amount
    assert not res[1]


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


def test_autoname_purchase_orders_exist_in_this_month_right_name(
    purchase_order: PurchaseOrder,
):
    this_month = get_this_month_ru_name()
    get_doc(PurchaseOrder, {"name": f"{this_month}-1"}).db_insert()
    purchase_order.autoname()
    assert purchase_order.name == f"{this_month}-2"


def test_autoname_purchase_orders_not_exist_in_this_month(
    purchase_order: PurchaseOrder,
):
    purchase_order.autoname()
    assert purchase_order.name == f"{get_this_month_ru_name()}-1"


def test_purchase_order_before_save(purchase_order: PurchaseOrder):
    purchase_order.delivery_options.append("somevalue")  # type: ignore
    purchase_order.before_save()
    assert len(purchase_order.delivery_options) == 0
    assert purchase_order.cannot_add_items is None


def test_purchase_order_before_insert(purchase_order: PurchaseOrder):
    purchase_order.status = None  # type: ignore
    purchase_order.before_insert()
    assert purchase_order.status == "Draft"


@pytest.mark.usefixtures("ikea_settings")
def test_purchase_order_before_submit(purchase_order: PurchaseOrder):
    purchase_order.db_insert()
    purchase_order.status = "Draft"
    purchase_order.get_delivery_services()
    purchase_order.before_submit()

    assert purchase_order.delivery_options == []
    assert purchase_order.cannot_add_items is None
    assert purchase_order.status == "To Receive"


def test_purchase_order_before_cancel(purchase_order: PurchaseOrder):
    purchase_order.status = "Draft"
    purchase_order.before_cancel()
    assert purchase_order.status == "Cancelled"


@pytest.mark.parametrize(
    "sales_order_item,item_to_sell,sales_order_should_change",
    (("10014030", "29128569", True), ("29128569", "10014030", False)),
)
def test_purchase_order_fetch_items_specs(
    monkeypatch: pytest.MonkeyPatch,
    purchase_order: PurchaseOrder,
    sales_order: SalesOrder,
    sales_order_item: str,
    item_to_sell: str,
    sales_order_should_change: bool,
):
    exp_item_codes = ["10014030", "29128569"]

    called_fetch_items = False

    def mock_fetch_items(item_codes: list[str], force_update: bool):
        assert force_update == True
        assert not set(item_codes) ^ set(exp_item_codes)

        nonlocal called_fetch_items
        called_fetch_items = True

        return FetchItemsResult(unsuccessful=["29128569"], successful=["10014030"])

    monkeypatch.setattr(
        comfort.transactions.doctype.purchase_order.purchase_order,
        "fetch_items",
        mock_fetch_items,
    )

    sales_order.reload()
    sales_order.items = []
    sales_order.append("items", {"item_code": sales_order_item, "qty": 1})
    sales_order.save()

    new_sales_order = new_doc(SalesOrder)
    new_sales_order.__newname = "testname"  # type: ignore
    new_sales_order.customer = sales_order.customer
    new_sales_order.append("items", {"item_code": sales_order_item, "qty": 1})
    new_sales_order.submit()

    purchase_order.items_to_sell = []
    purchase_order.append("items_to_sell", {"item_code": item_to_sell, "qty": 1})
    purchase_order.append("sales_orders", {"sales_order_name": new_sales_order.name})
    purchase_order.insert()

    purchase_order.reload()
    sales_order.reload()
    new_sales_order.reload()
    purchase_order_before = deepcopy(purchase_order)
    sales_order_before = deepcopy(sales_order)
    new_sales_order_before = deepcopy(new_sales_order)
    purchase_order.fetch_items_specs()
    assert called_fetch_items

    purchase_order.reload()
    sales_order.reload()
    new_sales_order.reload()
    assert purchase_order.as_dict() != purchase_order_before.as_dict()

    if sales_order_should_change:
        assert sales_order.as_dict() != sales_order_before.as_dict()
        assert new_sales_order.as_dict() != new_sales_order_before.as_dict()
    else:
        assert sales_order.as_dict() == sales_order_before.as_dict()
        assert new_sales_order.as_dict() == new_sales_order_before.as_dict()

    assert "Information about items updated" in str(frappe.message_log)


def test_add_purchase_info_and_submit_info_loaded(purchase_order: PurchaseOrder):
    purchase_order.db_insert()
    purchase_id = "111111110"

    purchase_order.add_purchase_info_and_submit(
        purchase_id, purchase_info=mock_purchase_info.dict()  # type: ignore
    )
    assert purchase_order.schedule_date == mock_purchase_info.delivery_date
    assert purchase_order.posting_date == mock_purchase_info.purchase_date
    assert purchase_order.delivery_cost == mock_purchase_info.delivery_cost
    assert purchase_order.order_confirmation_no == purchase_id
    assert purchase_order.docstatus == 1


def test_add_purchase_info_and_submit_info_not_loaded(purchase_order: PurchaseOrder):
    purchase_id, delivery_cost = "111111110", 2199
    purchase_order.db_insert()
    purchase_order.add_purchase_info_and_submit(
        purchase_id,
        purchase_info=PurchaseInfoDict(
            delivery_cost=delivery_cost,
            total_cost=0,
            purchase_date=datetime.now().date(),
            delivery_date=None,
        ),
    )
    assert purchase_order.schedule_date is None
    assert purchase_order.posting_date == getdate(today())
    assert purchase_order.delivery_cost == delivery_cost
    assert purchase_order.order_confirmation_no == purchase_id
    assert purchase_order.docstatus == 1


def test_purchase_order_checkout(
    monkeypatch: pytest.MonkeyPatch, purchase_order: PurchaseOrder
):
    called_add_items_to_cart = False

    def mock_add_items_to_cart(items: dict[str, int], authorize: bool):
        assert authorize == True
        assert items == purchase_order._get_templated_items_for_api(False)
        nonlocal called_add_items_to_cart
        called_add_items_to_cart = True

    monkeypatch.setattr(
        comfort.transactions.doctype.purchase_order.purchase_order,
        "add_items_to_cart",
        mock_add_items_to_cart,
    )
    purchase_order.checkout()
    assert called_add_items_to_cart


def test_purchase_order_add_receipt(
    monkeypatch: pytest.MonkeyPatch, purchase_order: PurchaseOrder
):
    purchase_order.name = "test"
    purchase_order.db_insert()
    called_create_receipt = False
    called_submit_sales_orders_and_update_statuses = False

    def mock_create_receipt(doctype: str, name: str):
        assert doctype == purchase_order.doctype
        assert name == purchase_order.name
        nonlocal called_create_receipt
        called_create_receipt = True

    monkeypatch.setattr(
        comfort.transactions.doctype.purchase_order.purchase_order,
        "create_receipt",
        mock_create_receipt,
    )

    class MockPurchaseOrder(PurchaseOrder):
        def _submit_sales_orders_and_update_statuses(self):
            nonlocal called_submit_sales_orders_and_update_statuses
            called_submit_sales_orders_and_update_statuses = True

    purchase_order = MockPurchaseOrder(purchase_order.as_dict())

    purchase_order.add_receipt()
    assert purchase_order.status == "Completed"
    assert called_create_receipt
    assert called_submit_sales_orders_and_update_statuses


def test_purchase_order_calculate_total_weight_and_total_weight_frontend(
    purchase_order: PurchaseOrder,
):
    purchase_order.insert()
    total_weight, total_margin = calculate_total_weight_and_total_weight(
        purchase_order.as_json()
    )
    purchase_order._calculate_total_weight()
    purchase_order._calculate_total_margin()
    assert total_weight == purchase_order.total_weight
    assert total_margin == purchase_order.total_margin
