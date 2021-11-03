from __future__ import annotations

from copy import copy, deepcopy
from datetime import datetime, timedelta
from types import SimpleNamespace
from typing import Any, Callable, Literal

import pytest
from ikea_api_wrapped.types import DeliveryOptionDict, UnavailableItemDict

import comfort.transactions.doctype.sales_order.sales_order
import frappe
from comfort import count_qty, counters_are_same, get_all, get_doc, get_value, new_doc
from comfort.comfort_core.doctype.commission_settings.commission_settings import (
    CommissionSettings,
)
from comfort.entities.doctype.child_item.child_item import ChildItem
from comfort.entities.doctype.item.item import Item
from comfort.finance import create_payment
from comfort.finance.doctype.payment.payment import Payment
from comfort.integrations.ikea import FetchItemsResult
from comfort.stock.doctype.checkout.checkout import Checkout
from comfort.stock.doctype.delivery_stop.delivery_stop import DeliveryStop
from comfort.stock.doctype.receipt.receipt import Receipt
from comfort.stock.doctype.stock_entry.stock_entry import StockEntry
from comfort.transactions.doctype.purchase_order.purchase_order import PurchaseOrder
from comfort.transactions.doctype.purchase_order_item_to_sell.purchase_order_item_to_sell import (
    PurchaseOrderItemToSell,
)
from comfort.transactions.doctype.sales_order.sales_order import (
    SalesOrder,
    _CheckAvailabilityCannotAddItem,
    _CheckAvailabilityDeliveryOptionItem,
    _SplitOrderItem,
    calculate_commission_and_margin,
    get_sales_orders_in_purchase_order,
    get_sales_orders_not_in_purchase_order,
    has_linked_delivery_trip,
    validate_params_from_available_stock,
)
from comfort.transactions.doctype.sales_order_child_item.sales_order_child_item import (
    SalesOrderChildItem,
)
from comfort.transactions.doctype.sales_order_item.sales_order_item import (
    SalesOrderItem,
)
from comfort.transactions.doctype.sales_return.sales_return import SalesReturn
from frappe import ValidationError
from tests.conftest import mock_delivery_services


def test_update_items_from_db(sales_order: SalesOrder):
    for i in sales_order.items:
        frappe.clear_document_cache("Item", i.item_code)

    sales_order.update_items_from_db()

    for i in sales_order.items:
        doc = get_doc(Item, i.item_code)
        assert i.item_name == doc.item_name
        assert i.rate == doc.rate
        assert i.weight == doc.weight


def test_set_child_items_not_set(sales_order: SalesOrder):
    sales_order.items = []
    sales_order.set_child_items()
    assert sales_order.child_items == []


def test_set_child_items_set(sales_order: SalesOrder, item: Item):
    sales_order.items[0].qty = 2
    sales_order.set_child_items()

    item_code_qty_pairs = count_qty(sales_order.child_items).items()
    for child in item.child_items:
        child.qty = child.qty * sales_order.items[0].qty

    for p in count_qty(item.child_items).items():
        assert p in item_code_qty_pairs


def patch_get_stock_balance(monkeypatch: pytest.MonkeyPatch, result: dict[str, int]):
    import comfort.transactions.doctype.sales_order.sales_order

    mock_get_stock_balance: Callable[[str], dict[str, int]] = lambda stock_type: result
    monkeypatch.setattr(
        comfort.transactions.doctype.sales_order.sales_order,
        "get_stock_balance",
        mock_get_stock_balance,
    )


def test_validate_from_available_stock_not_from_available_stock(
    sales_order: SalesOrder,
):
    sales_order.from_available_stock = None
    sales_order._validate_from_available_stock()


def test_validate_from_available_stock_available_actual_raises(
    monkeypatch: pytest.MonkeyPatch, sales_order: SalesOrder
):
    sales_order.from_available_stock = "Available Actual"
    sales_order.set_child_items()
    mock_stock_counter = count_qty(sales_order.get_items_with_splitted_combinations())
    item_code = list(mock_stock_counter.keys())[0]
    mock_stock_counter[item_code] -= 1
    patch_get_stock_balance(monkeypatch, mock_stock_counter)
    with pytest.raises(
        ValidationError, match=f"Insufficient stock for Item {item_code}"
    ):
        sales_order._validate_from_available_stock()


def test_validate_from_available_stock_available_actual_not_raises(
    monkeypatch: pytest.MonkeyPatch, sales_order: SalesOrder
):
    sales_order.from_available_stock = "Available Actual"
    sales_order.set_child_items()
    mock_stock_counter = count_qty(sales_order.get_items_with_splitted_combinations())
    patch_get_stock_balance(monkeypatch, mock_stock_counter)
    sales_order._validate_from_available_stock()


def test_validate_from_available_stock_available_purchased_raises(
    sales_order: SalesOrder, purchase_order: PurchaseOrder
):
    purchase_order.status = "To Receive"
    purchase_order.db_insert()
    purchase_order.update_children()
    sales_order.from_available_stock = "Available Purchased"
    sales_order.from_purchase_order = purchase_order.name
    sales_order.items = []
    sales_order.child_items = []
    sales_order.append(
        "items",
        {
            "item_code": purchase_order.items_to_sell[0].item_code,
            "qty": purchase_order.items_to_sell[0].qty + 1,
        },
    )
    with pytest.raises(
        ValidationError,
        match=f"Insufficient stock for Item {purchase_order.items_to_sell[0].item_code}",
    ):
        sales_order._validate_from_available_stock()


def test_validate_from_available_stock_available_purchased_not_raises(
    sales_order: SalesOrder, purchase_order: PurchaseOrder
):
    purchase_order.status = "To Receive"
    purchase_order.db_insert()
    purchase_order.update_children()
    sales_order.from_available_stock = "Available Purchased"
    sales_order.from_purchase_order = purchase_order.name
    sales_order.items = []
    sales_order.child_items = []
    sales_order.append(
        "items",
        {
            "item_code": purchase_order.items_to_sell[0].item_code,
            "qty": purchase_order.items_to_sell[0].qty,
        },
    )
    sales_order._validate_from_available_stock()


def test_calculate_item_totals(sales_order: SalesOrder):
    sales_order.update_items_from_db()

    exp_total_quantity, exp_total_weight, exp_items_cost = 0, 0.0, 0
    for i in sales_order.items:
        assert i.amount == i.qty * i.rate
        assert i.total_weight == i.qty * i.weight

        exp_total_quantity += i.qty
        exp_total_weight += i.total_weight
        exp_items_cost += i.amount

    sales_order._calculate_item_totals()

    assert exp_total_quantity == sales_order.total_quantity
    assert exp_total_weight == sales_order.total_weight
    assert exp_items_cost == sales_order.items_cost


def test_calculate_service_amount(sales_order: SalesOrder):
    sales_order._calculate_service_amount()
    service_amount = sum(s.rate for s in sales_order.services)

    assert service_amount == sales_order.service_amount


def test_calculate_commission_no_edit_commission(sales_order: SalesOrder):
    sales_order.items_cost = 5309
    sales_order._calculate_commission()

    assert sales_order.commission == CommissionSettings.get_commission_percentage(
        sales_order.items_cost
    )


def test_calculate_commission_with_edit_commission(sales_order: SalesOrder):
    sales_order.edit_commission = True
    sales_order.commission = 100
    sales_order.items_cost = 21094
    sales_order._calculate_commission()

    assert sales_order.commission == 100


def test_calculate_commission_items_cost_is_zero(sales_order: SalesOrder):
    sales_order.items_cost = 0
    sales_order._calculate_commission()
    assert sales_order.commission == None


@pytest.mark.parametrize("items_cost", (0, -10))
def test_calculate_margin_zero_if_items_cost_is_zero_or_less(
    sales_order: SalesOrder, items_cost: int
):
    sales_order.items_cost = items_cost
    sales_order._calculate_margin()
    assert sales_order.margin == 0


def test_calculate_margin_without_commission(sales_order: SalesOrder):
    sales_order.commission = 0
    sales_order.items_cost = 21214
    sales_order._calculate_margin()
    assert sales_order.margin == -4


def test_calculate_margin_with_commission(sales_order: SalesOrder):
    sales_order.commission = 15
    sales_order.items_cost = 1494
    sales_order._calculate_margin()

    base_margin = sales_order.items_cost * sales_order.commission / 100
    items_cost_rounding_remainder = (
        round(sales_order.items_cost, -1) - sales_order.items_cost
    )
    rounded_margin = round(base_margin, -1) + items_cost_rounding_remainder

    assert rounded_margin == sales_order.margin


def test_calculate_total_amount(sales_order: SalesOrder):
    sales_order.items_cost = 14984
    sales_order.margin = 1496
    sales_order.service_amount = 300
    sales_order.discount = 100
    sales_order._calculate_total_amount()
    exp_total_amount = (
        sales_order.items_cost
        + sales_order.margin
        + sales_order.service_amount
        - sales_order.discount
    )
    assert sales_order.total_amount == exp_total_amount


@pytest.mark.parametrize("delivery_status", ("", "Delivered"))
def test_validate_services_not_changed_raises_on_changed_value(
    sales_order: SalesOrder, delivery_status: Literal["", "Delivered"]
):
    sales_order.insert()
    sales_order.db_set("delivery_status", delivery_status)
    sales_order.services[0].rate += 300
    with pytest.raises(
        ValidationError,
        match="Allowed to change services in Sales Order only if delivery status is To Purchase, Purchased or To Deliver",
    ):
        sales_order._validate_services_not_changed()


def test_validate_services_not_changed_raises_on_added_item(sales_order: SalesOrder):
    sales_order.insert()
    sales_order.db_set("delivery_status", "Delivered")
    sales_order.append("services", {"type": "Installation", "rate": 200})
    with pytest.raises(
        ValidationError,
        match="Allowed to change services in Sales Order only if delivery status is To Purchase, Purchased or To Deliver",
    ):
        sales_order._validate_services_not_changed()


def test_validate_services_not_changed_raises_on_removed_item(sales_order: SalesOrder):
    sales_order.insert()
    sales_order.db_set("delivery_status", "Delivered")
    sales_order.services.pop()
    with pytest.raises(
        ValidationError,
        match="Allowed to change services in Sales Order only if delivery status is To Purchase, Purchased or To Deliver",
    ):
        sales_order._validate_services_not_changed()


@pytest.mark.parametrize(
    "delivery_status",
    (
        "To Purchase",
        "Purchased",
        "To Deliver",
    ),
)
def test_validate_services_not_changed_not_raises_on_status(
    sales_order: SalesOrder,
    delivery_status: Literal["To Purchase", "Purchased", "To Deliver"],
):
    sales_order.insert()
    sales_order.db_set("delivery_status", delivery_status)
    sales_order.services[0].rate += 300
    sales_order._validate_services_not_changed()


def test_validate_services_not_changed_not_raises_if_value_not_changed(
    sales_order: SalesOrder,
):
    sales_order.insert()
    sales_order.db_set("delivery_status", "Delivered")
    sales_order._validate_services_not_changed()


def test_get_sales_order_items_with_splitted_combinations(sales_order: SalesOrder):
    sales_order.set_child_items()
    items = sales_order.get_items_with_splitted_combinations()
    parents: set[str] = set()
    for child in sales_order.child_items:
        assert child in items
        parents.add(child.parent_item_code)

    for i in sales_order.items:
        if i.item_code in parents:
            assert i not in items
        else:
            assert i in items


def test_create_cancel_sales_return_without_return_before(
    purchase_order: PurchaseOrder, sales_order: SalesOrder
):
    purchase_order.db_insert()
    purchase_order.update_children()
    sales_order.docstatus = 1
    sales_order.db_update()
    sales_order.update_children()
    sales_order.db_set("delivery_status", "Purchased")
    sales_order.docstatus = 2
    sales_order.validate()
    sales_order.load_doc_before_save()
    sales_order._create_cancel_sales_return()

    assert len(get_all(SalesReturn)) == 1
    return_name: str = get_value("Sales Return", {"sales_order": sales_order.name})
    cancel_return = get_doc(SalesReturn, return_name)
    assert cancel_return.sales_order == sales_order.name
    assert counters_are_same(
        count_qty(sales_order.get_items_with_splitted_combinations()),
        count_qty(cancel_return.items),
    )


def test_create_cancel_sales_return_with_return_before(
    sales_return: SalesReturn, purchase_order: PurchaseOrder
):
    purchase_order.db_insert()
    purchase_order.update_children()
    sales_order = sales_return._voucher
    prev_counter = count_qty(sales_order.get_items_with_splitted_combinations())
    sales_order.docstatus = 1
    sales_order.db_update()
    sales_order.update_children()
    sales_order.db_set("delivery_status", "Purchased")

    sales_return.insert()
    prev_return_counter = count_qty(sales_return.items)
    sales_return.submit()

    sales_order.docstatus = 2
    sales_order.validate()
    sales_order.load_doc_before_save()
    sales_order._create_cancel_sales_return()

    assert len(get_all(SalesReturn)) == 2
    return_name: str = get_value("Sales Return", {"sales_order": sales_order.name})
    cancel_return = get_doc(SalesReturn, return_name)
    new_counter = count_qty(sales_order.get_items_with_splitted_combinations())

    assert cancel_return.sales_order == sales_order.name
    assert counters_are_same(new_counter, count_qty(cancel_return.items))
    assert counters_are_same(prev_counter, new_counter + prev_return_counter)


def test_modify_purchase_order_for_from_available_stock_not_available_purchased(
    sales_order: SalesOrder,
):
    sales_order.from_available_stock = "Available Actual"
    sales_order._modify_purchase_order_for_from_available_stock()


def test_modify_purchase_order_for_from_available_stock_available_purchased(
    sales_order: SalesOrder, purchase_order: PurchaseOrder
):
    purchase_order.sales_orders = []
    purchase_order.items_to_sell[0].qty = 1
    purchase_order.db_insert()
    purchase_order.update_children()
    sales_order.items = []
    sales_order.child_items = []
    sales_order.append(
        "items",
        {
            "item_code": purchase_order.items_to_sell[0].item_code,
            "qty": purchase_order.items_to_sell[0].qty,
        },
    )
    sales_order.set_child_items()
    sales_order.from_available_stock = "Available Purchased"
    sales_order.from_purchase_order = purchase_order.name

    def get_po_counter(purchase_order: PurchaseOrder):
        items: list[
            SalesOrderItem | SalesOrderChildItem | PurchaseOrderItemToSell | ChildItem
        ] = list(purchase_order.get_items_in_sales_orders(True))
        items += purchase_order.get_items_to_sell(True)
        print(count_qty(purchase_order.get_items_to_sell(True)))
        print(count_qty(purchase_order.get_items_in_sales_orders(True)))
        return count_qty(items)

    prev_counter = get_po_counter(purchase_order)
    sales_order._modify_purchase_order_for_from_available_stock()

    sales_order.db_update()
    sales_order.update_children()
    purchase_order.reload()
    assert counters_are_same(prev_counter, get_po_counter(purchase_order))


def test_make_stock_entries_for_from_available_stock_not_executed(
    sales_order: SalesOrder,
):
    sales_order.from_available_stock = None
    sales_order._make_stock_entries_for_from_available_stock()
    assert len(get_all(StockEntry)) == 0


@pytest.mark.usefixtures("ikea_settings")
def test_make_stock_entries_for_from_available_stock_available_purchased(
    sales_order: SalesOrder, purchase_order: PurchaseOrder
):
    purchase_order.db_insert()
    purchase_order.update_children()

    sales_order.from_available_stock = "Available Purchased"
    sales_order.from_purchase_order = purchase_order.name

    checkout = get_doc(
        Checkout, {"purchase_order": purchase_order.name, "docstatus": 1}
    )
    checkout.db_insert()
    sales_order._make_stock_entries_for_from_available_stock()

    exp_counter = count_qty(sales_order.get_items_with_splitted_combinations())
    for e in get_all(StockEntry):
        entry = get_doc(StockEntry, e.name)
        assert entry.stock_type in ("Available Purchased", "Reserved Purchased")
        if entry.stock_type == "Available Purchased":
            for item in entry.items:
                item.qty = -item.qty
            assert count_qty(entry.items) == exp_counter
        else:
            assert count_qty(entry.items) == exp_counter


def test_make_stock_entries_for_from_available_stock_available_actual(
    sales_order: SalesOrder,
):
    sales_order.from_available_stock = "Available Actual"
    sales_order.db_insert()
    sales_order.child_items = []
    sales_order._make_stock_entries_for_from_available_stock()

    exp_counter = count_qty(sales_order.get_items_with_splitted_combinations())
    for e in get_all(StockEntry):
        entry = get_doc(StockEntry, e.name)
        assert entry.stock_type in ("Available Actual", "Reserved Actual")
        if entry.stock_type == "Available Actual":
            for item in entry.items:
                item.qty = -item.qty
            assert count_qty(entry.items) == exp_counter
        else:
            assert count_qty(entry.items) == exp_counter


def test_get_paid_amount(sales_order: SalesOrder):
    sales_order.db_insert()
    create_payment(sales_order.doctype, sales_order.name, 300, paid_with_cash=True)
    assert sales_order._get_paid_amount() == 300


def test_get_paid_amount_with_returns(sales_return: SalesReturn):
    sales_order = sales_return._voucher
    sales_order.add_payment(sales_order.total_amount, cash=True)
    sales_return.db_insert()
    sales_return._calculate_returned_paid_amount()
    assert sales_return.returned_paid_amount > 0

    exp_amount = sales_order.total_amount - sales_return.returned_paid_amount
    sales_order.delivery_status = "To Deliver"
    sales_return._make_payment_gl_entries()
    sales_return._make_delivery_gl_entries()
    assert sales_order._get_paid_amount() == exp_amount


@pytest.mark.parametrize(
    "total_amount,paid_amount,exp_per_paid,exp_pending_amount",
    ((10, 10, 100.0, 0), (500, 250, 50.0, 250)),
)
def test_set_paid_and_pending_per_amount(
    sales_order: SalesOrder,
    total_amount: int,
    paid_amount: int,
    exp_per_paid: float,
    exp_pending_amount: int,
):
    sales_order.db_insert()
    create_payment(sales_order.doctype, sales_order.name, paid_amount, True)

    sales_order.total_amount = total_amount
    sales_order.set_paid_and_pending_per_amount()

    assert sales_order.paid_amount == paid_amount
    assert sales_order.per_paid == exp_per_paid
    assert sales_order.pending_amount == exp_pending_amount


def test_set_paid_and_pending_per_amount_with_zero_total_amount(
    sales_order: SalesOrder,
):
    sales_order.total_amount = 0
    sales_order.set_paid_and_pending_per_amount()

    assert sales_order.paid_amount == 0
    assert sales_order.per_paid == 100
    assert sales_order.pending_amount == 0


def test_set_payment_status_with_cancelled_status(sales_order: SalesOrder):
    sales_order.docstatus = 2
    sales_order._set_payment_status()
    assert sales_order.payment_status == ""


@pytest.mark.parametrize(
    "per_paid,expected_status",
    (
        (120, "Overpaid"),
        (100, "Paid"),
        (50, "Partially Paid"),
        (0, "Unpaid"),
        (-20, "Unpaid"),
    ),
)
def test_set_payment_status(
    sales_order: SalesOrder, per_paid: int, expected_status: str
):
    sales_order.per_paid = per_paid
    sales_order._set_payment_status()
    assert sales_order.payment_status == expected_status


def test_set_delivery_status_to_purchase(sales_order: SalesOrder):
    sales_order._set_delivery_status()
    assert sales_order.delivery_status == "To Purchase"


def test_set_delivery_status_purchased(
    sales_order: SalesOrder, purchase_order: PurchaseOrder
):
    for order in purchase_order.sales_orders:
        order.docstatus = 1
    purchase_order.docstatus = 1
    purchase_order.db_update_all()

    sales_order._set_delivery_status()
    assert sales_order.delivery_status == "Purchased"


def test_set_delivery_status_to_deliver(
    sales_order: SalesOrder, purchase_order: PurchaseOrder, receipt_purchase: Receipt
):
    for order in purchase_order.sales_orders:
        order.docstatus = 1
    purchase_order.docstatus = 1
    purchase_order.db_update_all()

    receipt_purchase.docstatus = 1
    receipt_purchase.db_insert()

    sales_order._set_delivery_status()
    assert sales_order.delivery_status == "To Deliver"


def test_set_delivery_status_delivered(sales_order: SalesOrder, receipt_sales: Receipt):
    receipt_sales.docstatus = 1
    receipt_sales.db_insert()
    sales_order._set_delivery_status()
    assert sales_order.delivery_status == "Delivered"


def test_set_delivery_status_with_cancelled_status(sales_order: SalesOrder):
    sales_order.docstatus = 2
    sales_order._set_delivery_status()
    assert sales_order.delivery_status == ""


@pytest.mark.parametrize(
    ("docstatus", "exp_delivery_status"), ((0, "To Purchase"), (1, "To Deliver"))
)
def test_set_delivery_status_from_available_actual_stock_not_delivered(
    sales_order: SalesOrder, docstatus: int, exp_delivery_status: str
):
    sales_order.docstatus = docstatus
    sales_order.from_available_stock = "Available Actual"
    sales_order._set_delivery_status()
    assert sales_order.delivery_status == exp_delivery_status


def test_set_delivery_status_from_available_actual_stock_delivered(
    receipt_sales: Receipt,
):
    sales_order = get_doc(SalesOrder, receipt_sales.voucher_no)
    sales_order.from_available_stock = "Available Actual"
    receipt_sales.insert()
    receipt_sales.submit()
    sales_order._set_delivery_status()
    assert sales_order.delivery_status == "Delivered"


@pytest.mark.parametrize(
    "docstatus,payment_status,delivery_status,expected_status",
    (
        (0, None, None, "Draft"),
        (1, "Paid", "Delivered", "Completed"),
        (1, "Paid", None, "In Progress"),
        (1, None, "Delivered", "In Progress"),
        (1, None, None, "In Progress"),
        (2, None, None, "Cancelled"),
    ),
)
def test_set_document_status(
    sales_order: SalesOrder,
    docstatus: int,
    payment_status: str | None,
    delivery_status: str | None,
    expected_status: Literal["Draft", "In Progress", "Completed", "Cancelled"],
):
    sales_order.docstatus = docstatus
    sales_order.payment_status = payment_status  # type: ignore
    sales_order.delivery_status = delivery_status  # type: ignore
    sales_order._set_document_status()
    assert sales_order.status == expected_status


def test_sales_order_on_cancel(sales_order: SalesOrder):
    sales_order.update_items_from_db()
    sales_order.calculate()
    sales_order.db_insert()
    sales_order.update_children()
    sales_order.add_payment(100, cash=True)
    sales_order.db_set("delivery_status", "To Deliver")
    sales_order.add_receipt()

    sales_order.on_cancel()
    for doctype in (Payment, Receipt):
        docs = get_all(
            doctype,
            {"voucher_type": sales_order.doctype, "voucher_no": sales_order.name},
            "docstatus",
        )
        assert all(doc.docstatus == 2 for doc in docs)


def test_add_payment_raises(sales_order: SalesOrder):
    sales_order.docstatus = 2
    with pytest.raises(
        ValidationError,
        match="Sales Order should be not Сancelled to add Payment",
    ):
        sales_order.add_payment(100, True)


def test_add_payment_passes(sales_order: SalesOrder):
    sales_order.insert()
    sales_order.add_payment(100, True)
    payments = get_all(
        Payment,
        {"voucher_type": sales_order.doctype, "voucher_no": sales_order.name},
    )
    assert len(payments) == 1


@pytest.mark.parametrize(
    "delivery_status", ("", "To Purchase", "Purchased", "Delivered")
)
def test_add_receipt_raises_on_wrong_delivery_status(
    sales_order: SalesOrder,
    delivery_status: Literal["", "To Purchase", "Purchased", "Delivered"],
):
    sales_order.delivery_status = delivery_status
    with pytest.raises(
        ValidationError,
        match="Delivery Status Sales Order should be To Deliver to add Receipt",
    ):
        sales_order.add_receipt()


def test_add_receipt_passes(sales_order: SalesOrder):
    sales_order.insert()
    sales_order.db_set("delivery_status", "To Deliver")
    sales_order.add_receipt()
    receipts = get_all(
        Receipt,
        {"voucher_type": sales_order.doctype, "voucher_no": sales_order.name},
    )
    assert len(receipts) == 1
    assert sales_order.delivery_status == "Delivered"


@pytest.mark.parametrize("save", (True, False))
def test_split_combinations(sales_order: SalesOrder, save: bool):
    sales_order.db_insert()
    sales_order.db_update_all()
    sales_order.items = sales_order.items[:1]
    sales_order.items[0].qty = 3
    splitted_combination = deepcopy(sales_order.items[0])

    sales_order.split_combinations([splitted_combination.name], save)

    child_items = get_all(
        ChildItem,
        fields=("item_code", "qty"),
        filters={"parent": splitted_combination.item_code},
    )
    exp_item_codes_to_qty = count_qty(child_items)
    for i in exp_item_codes_to_qty:
        exp_item_codes_to_qty[i] *= 3
    exp_item_codes_to_qty = exp_item_codes_to_qty.items()

    for i in count_qty(sales_order.items).items():
        assert i in exp_item_codes_to_qty

    # load_doc_before_save is called before save,
    # so this is quite a hack to determine whether document is saved
    doc_was_saved = sales_order.get_doc_before_save() is not None
    assert doc_was_saved if save else not doc_was_saved


def test_get_customer_first_name_valid(sales_order: SalesOrder):
    assert sales_order._get_customer_first_name() == "Pavel"


def test_get_customer_first_name_not_valid(sales_order: SalesOrder):
    sales_order.customer = r"dfkj"
    assert sales_order._get_customer_first_name() == sales_order.customer


def test_get_check_order_message_context(sales_order: SalesOrder):
    sales_order.validate()
    context = sales_order._get_check_order_message_context()
    assert context["customer_first_name"] == sales_order._get_customer_first_name()
    assert counters_are_same(
        count_qty(context["items"]),  # type: ignore
        count_qty(sales_order.items),
    )
    assert context["services"] == sales_order.services
    assert context["total_amount"] == sales_order.total_amount


def test_generate_check_order_message(sales_order: SalesOrder):
    sales_order.validate()
    msg = sales_order.generate_check_order_message()
    assert msg is not None
    assert "check_order_message.j2" not in msg


def test_get_pickup_order_message_context(sales_order: SalesOrder):
    MONTHS = {
        1: "января",
        2: "февраля",
        3: "марта",
        4: "апреля",
        5: "мая",
        6: "июня",
        7: "июля",
        8: "августа",
        9: "сентября",
        10: "октября",
        11: "ноября",
        12: "декабря",
    }
    WEEKDAYS = {
        0: "в понедельник",
        1: "во вторник",
        2: "в среду",
        3: "в четверг",
        4: "в пятницу",
        5: "в субботу",
        6: "в воскресенье",
    }
    tomorrow = datetime.now() + timedelta(days=1)

    sales_order.validate()
    context = sales_order._get_pickup_order_message_context()
    assert context["customer_first_name"] == sales_order._get_customer_first_name()
    assert context["weekday"] == WEEKDAYS[tomorrow.weekday()]
    assert context["day"] == tomorrow.day
    assert context["month"] == MONTHS[tomorrow.month]
    assert context["has_delivery"] == True
    assert context["pending_amount"] == sales_order.pending_amount


def test_get_pickup_order_message_context_not_has_delivery(sales_order: SalesOrder):
    sales_order.services = []
    sales_order.validate()
    context = sales_order._get_pickup_order_message_context()
    assert context["has_delivery"] == False


def test_get_pickup_order_message_context_not_has_pending_amount(
    sales_order: SalesOrder,
):
    sales_order.validate()
    sales_order.pending_amount = 0
    context = sales_order._get_pickup_order_message_context()
    assert context["pending_amount"] == 0


def test_generate_pickup_order_message(sales_order: SalesOrder):
    sales_order.validate()
    msg = sales_order.generate_pickup_order_message()
    assert msg is not None
    assert "pickup_order_message.j2" not in msg


def test_get_services_for_check_availability_no_delivery_options(
    monkeypatch: pytest.MonkeyPatch, sales_order: SalesOrder
):
    def new_get_delivery_services(items: Any):
        pass

    monkeypatch.setattr(
        comfort.transactions.doctype.sales_order.sales_order,
        "get_delivery_services",
        new_get_delivery_services,
    )

    frappe.message_log = []
    items = count_qty(sales_order.get_items_with_splitted_combinations())
    assert sales_order._get_services_for_check_availability(items) is None
    assert frappe.message_log == []


def test_get_services_for_check_availability_no_unavailble_items(
    monkeypatch: pytest.MonkeyPatch,
    sales_order: SalesOrder,
):
    def new_get_delivery_services(items: Any):
        resp = deepcopy(mock_delivery_services)
        resp["cannot_add"] = []
        for option in resp["delivery_options"]:
            option["unavailable_items"] = []
        return resp

    monkeypatch.setattr(
        comfort.transactions.doctype.sales_order.sales_order,
        "get_delivery_services",
        new_get_delivery_services,
    )

    items = count_qty(sales_order.get_items_with_splitted_combinations())
    assert sales_order._get_services_for_check_availability(items) is None
    assert "All items available" in str(frappe.message_log)  # type: ignore


@pytest.mark.parametrize(
    ("cannot_add_appear", "unavailable_items_appear"),
    (
        (True, False),
        (False, True),
        (True, True),
    ),
)
def test_get_services_for_check_availability_with_unavailable_items(
    monkeypatch: pytest.MonkeyPatch,
    sales_order: SalesOrder,
    cannot_add_appear: bool,
    unavailable_items_appear: bool,
):
    resp = deepcopy(mock_delivery_services)
    if not cannot_add_appear:
        resp["cannot_add"] = []
    if not unavailable_items_appear:
        for option in resp["delivery_options"]:
            option["unavailable_items"] = []

    def new_get_delivery_services(items: Any):
        return resp

    monkeypatch.setattr(
        comfort.transactions.doctype.sales_order.sales_order,
        "get_delivery_services",
        new_get_delivery_services,
    )

    frappe.message_log = []
    items = count_qty(sales_order.get_items_with_splitted_combinations())
    assert sales_order._get_services_for_check_availability(items) == resp
    assert frappe.message_log == []


def test_check_availability_options_items(
    monkeypatch: pytest.MonkeyPatch, sales_order: SalesOrder
):
    item = sales_order.items[0]

    def new_get_delivery_services(items: Any):
        resp = deepcopy(mock_delivery_services)
        resp["cannot_add"] = []
        resp["delivery_options"] = resp["delivery_options"][:1]
        resp["delivery_options"][0]["unavailable_items"] = [
            UnavailableItemDict(item_code=item.item_code, available_qty=0)
        ]
        resp["delivery_options"].append(
            DeliveryOptionDict(
                delivery_date=None,
                delivery_type="test",
                price=0,
                service_provider=None,
                unavailable_items=[],
            )
        )
        return resp

    monkeypatch.setattr(
        comfort.transactions.doctype.sales_order.sales_order,
        "get_delivery_services",
        new_get_delivery_services,
    )

    resp = sales_order.check_availability()
    assert resp is not None
    assert len(resp["options"]) == 1
    option = resp["options"][0]
    assert len(option["items"]) == 1
    assert option["items"][0] == _CheckAvailabilityDeliveryOptionItem(
        item_code=item.item_code,
        item_name=item.item_name,
        available_qty=0,
        required_qty=item.qty,
    )


@pytest.mark.parametrize(
    ("service_provider", "delivery_type", "exp_delivery_type"),
    (
        ("Provider", "Type", "Type (Provider)"),
        (None, "Type", "Type"),
    ),
)
def test_check_availability_options_delivery_type(
    monkeypatch: pytest.MonkeyPatch,
    sales_order: SalesOrder,
    service_provider: str | None,
    delivery_type: str,
    exp_delivery_type: str,
):
    def new_get_delivery_services(items: Any):
        resp = deepcopy(mock_delivery_services)
        resp["cannot_add"] = []
        resp["delivery_options"] = resp["delivery_options"][:1]
        option = resp["delivery_options"][0]
        option["service_provider"] = service_provider
        option["delivery_type"] = delivery_type
        option["unavailable_items"] = [
            UnavailableItemDict(
                item_code=sales_order.items[0].item_code, available_qty=0
            )
        ]
        return resp

    monkeypatch.setattr(
        comfort.transactions.doctype.sales_order.sales_order,
        "get_delivery_services",
        new_get_delivery_services,
    )

    resp = sales_order.check_availability()
    assert resp is not None
    assert resp["options"][0]["delivery_type"] == exp_delivery_type


def test_check_availability_options_cannot_add(
    monkeypatch: pytest.MonkeyPatch,
    sales_order: SalesOrder,
):
    item = sales_order.items[0]

    def new_get_delivery_services(items: Any):
        resp = deepcopy(mock_delivery_services)
        resp["cannot_add"] = [item.item_code]
        resp["delivery_options"] = resp["delivery_options"][:1]
        resp["delivery_options"][0]["unavailable_items"] = []
        return resp

    monkeypatch.setattr(
        comfort.transactions.doctype.sales_order.sales_order,
        "get_delivery_services",
        new_get_delivery_services,
    )

    resp = sales_order.check_availability()
    assert resp is not None
    assert len(resp["cannot_add"]) == 1
    assert resp["cannot_add"][0] == _CheckAvailabilityCannotAddItem(
        item_code=item.item_code, item_name=item.item_name
    )


def test_check_availability_no_delivery_services(
    monkeypatch: pytest.MonkeyPatch,
    sales_order: SalesOrder,
):
    def new_get_delivery_services(items: Any):
        pass

    monkeypatch.setattr(
        comfort.transactions.doctype.sales_order.sales_order,
        "get_delivery_services",
        new_get_delivery_services,
    )

    assert sales_order.check_availability() is None


def test_sales_order_fetch_items_specs_raises_on_from_available_stock(
    sales_order: SalesOrder,
):
    sales_order.from_available_stock = "Available Purchased"
    sales_order.db_insert()
    with pytest.raises(
        ValidationError,
        match="Can't fetch items specs if order is from Available Stock",
    ):
        sales_order.fetch_items_specs()


@pytest.mark.parametrize("status", ("In Progress", "Completed", "Cancelled"))
def test_sales_order_fetch_items_specs_raises_on_not_draft(
    sales_order: SalesOrder, status: Literal["In Progress", "Completed", "Cancelled"]
):
    sales_order.status = status
    sales_order.db_insert()
    with pytest.raises(
        ValidationError, match="Can fetch items specs only if status is Draft"
    ):
        sales_order.fetch_items_specs()


@pytest.mark.parametrize(
    ("successful", "unsuccessful"),
    ((["29128569"], ["10014030"]), (["29128569", "10014030"], [])),
)
def test_sales_order_fetch_items_specs_passes(
    monkeypatch: pytest.MonkeyPatch,
    sales_order: SalesOrder,
    successful: list[str],
    unsuccessful: list[str],
):
    called_fetch_items = False

    def mock_fetch_items(item_codes: list[str], force_update: bool):
        assert force_update == True
        assert item_codes == [i.item_code for i in sales_order.items]
        nonlocal called_fetch_items
        called_fetch_items = True
        return FetchItemsResult(successful=successful, unsuccessful=unsuccessful)

    monkeypatch.setattr(
        comfort.transactions.doctype.sales_order.sales_order,
        "fetch_items",
        mock_fetch_items,
    )

    sales_order.insert()
    sales_order.reload()
    doc_before = copy(sales_order)

    sales_order.fetch_items_specs()
    assert called_fetch_items
    sales_order.reload()
    assert sales_order.as_dict() != doc_before.as_dict()
    if unsuccessful:
        assert f"Cannot fetch those items: {', '.join(unsuccessful)}" in str(
            frappe.message_log  # type: ignore
        )


def test_validate_split_order_counters_are_same(sales_order: SalesOrder):
    counter = count_qty(sales_order.items)
    with pytest.raises(
        ValidationError, match="Can't split Sales Order and include all the items"
    ):
        sales_order._validate_split_order(counter)


def test_validate_split_order_no_such_item(sales_order: SalesOrder):
    counter = count_qty(sales_order.items)
    item_code = "random item code"
    counter[item_code] = 10

    with pytest.raises(ValidationError, match=f"No Item {item_code} in Sales Order"):
        sales_order._validate_split_order(counter)


def test_validate_split_order_insufficient_qty(sales_order: SalesOrder):
    counter = count_qty(sales_order.items)
    item_code = list(counter.keys())[0]
    qty_before = counter[item_code]
    counter[item_code] += 1
    qty_after = counter[item_code]

    with pytest.raises(
        ValidationError,
        match=f"Insufficient quantity for Item {item_code}. Available: {qty_before}, you have: {qty_after}",
    ):
        sales_order._validate_split_order(counter)


def test_split_order(sales_order: SalesOrder):
    # Remove items and move child items to ordinary items
    sales_order.set_child_items()
    sales_order.items = []
    sales_order.extend(
        "items",
        [
            {"item_code": child.item_code, "qty": 30}
            for child in sales_order.child_items
        ],
    )
    sales_order.insert()

    counter_before = count_qty(sales_order.items)

    item_code, qty = list(count_qty(sales_order.items).items())[0]
    items_to_split: list[_SplitOrderItem] = [{"item_code": item_code, "qty": qty}]

    new_doc_name = sales_order.split_order(items_to_split)

    assert sales_order.edit_commission == True
    exp_counter = counter_before.copy()
    del exp_counter[item_code]
    assert count_qty(sales_order.items) == exp_counter

    new_doc = get_doc(SalesOrder, new_doc_name)
    assert new_doc.customer == sales_order.customer
    assert count_qty(new_doc.items) == count_qty(
        (SimpleNamespace(**items_to_split[0]),)
    )
    assert new_doc.commission == sales_order.commission
    assert new_doc.edit_commission == True


def test_has_linked_delivery_trip_true(sales_order: SalesOrder):
    sales_order.db_insert()
    get_doc(DeliveryStop, {"sales_order": sales_order.name}).db_insert()
    assert has_linked_delivery_trip(sales_order.name)


def test_has_linked_delivery_trip_false(sales_order: SalesOrder):
    sales_order.db_insert()
    assert not has_linked_delivery_trip(sales_order.name)


def test_get_sales_orders_not_in_purchase_order_main(purchase_order: PurchaseOrder):
    purchase_order.db_insert()
    purchase_order.db_update_all()
    new_sales_order = get_doc(SalesOrder, {"name": "mytestname"})
    new_sales_order.db_insert()

    res = get_sales_orders_not_in_purchase_order()
    assert purchase_order.sales_orders[0].sales_order_name not in res
    assert new_sales_order.name in res


def test_get_sales_orders_not_in_purchase_order_cancelled_po(
    purchase_order: PurchaseOrder,
):
    purchase_order.docstatus = 2
    purchase_order.set_docstatus()
    purchase_order.db_insert()
    purchase_order.update_children()
    new_sales_order = get_doc(SalesOrder, {"name": "mytestname"})
    new_sales_order.db_insert()

    res = get_sales_orders_not_in_purchase_order()
    assert purchase_order.sales_orders[0].sales_order_name in res
    assert new_sales_order.name in res


@pytest.mark.parametrize(
    "from_available_stock", ("Available Purchased", "Available Actual")
)
def test_get_sales_orders_not_in_purchase_order_from_available_stock(
    sales_order: SalesOrder,
    from_available_stock: Literal["Available Purchased", "Available Actual"],
):
    sales_order.insert()

    new_sales_order = new_doc(SalesOrder)
    new_sales_order.from_available_stock = from_available_stock
    new_sales_order.db_insert()

    res = get_sales_orders_not_in_purchase_order()
    assert sales_order.name in res
    assert new_sales_order.name not in res


def test_get_sales_orders_not_in_purchase_order_cancelled(sales_order: SalesOrder):
    sales_order.docstatus = 2
    sales_order.db_insert()

    res = get_sales_orders_not_in_purchase_order()
    assert sales_order.name not in res


def test_get_sales_orders_in_purchase_order(purchase_order: PurchaseOrder):
    purchase_order.db_insert()
    purchase_order.update_children()

    new_sales_order = new_doc(SalesOrder)
    new_sales_order.name = "mytestname"
    new_sales_order.db_insert()

    res = get_sales_orders_in_purchase_order(purchase_order.name)
    assert purchase_order.sales_orders[0].sales_order_name in res
    assert new_sales_order.name not in res


def test_params_validate_from_available_stock_not_from_available_stock(
    sales_order: SalesOrder,
):
    sales_order.from_available_stock = sales_order.from_purchase_order = None
    validate_params_from_available_stock(
        sales_order.from_available_stock, sales_order.from_purchase_order
    )


def test_params_validate_from_available_stock_available_purchased_raises_on_no_from_purchase_order():
    with pytest.raises(
        ValidationError,
        match="If From Available Stock is Available Purchased, From Purchase Order should be set",
    ):
        validate_params_from_available_stock("Available Purchased", None)


@pytest.mark.parametrize("status", ("Draft", "Completed", "Cancelled"))
def test_params_validate_from_available_stock_available_purchased_raises_on_wrong_po_status(
    purchase_order: PurchaseOrder, status: Literal["Draft", "Completed", "Cancelled"]
):
    purchase_order.status = status
    purchase_order.set_new_name()
    purchase_order.db_insert()
    with pytest.raises(
        ValidationError, match="Status of Purchase Order should be To Receive"
    ):
        validate_params_from_available_stock("Available Purchased", purchase_order.name)


def test_params_validate_from_available_stock_available_purchased_raises_on_no_items_to_sell(
    purchase_order: PurchaseOrder,
):
    purchase_order.status = "To Receive"
    purchase_order.items_to_sell = []
    purchase_order.db_insert()
    purchase_order.update_children()
    with pytest.raises(
        ValidationError, match="Selected Purchase Order has no Items To Sell"
    ):
        validate_params_from_available_stock("Available Purchased", purchase_order.name)


def test_params_validate_from_available_stock_available_purchased_passes(
    purchase_order: PurchaseOrder,
):
    purchase_order.status = "To Receive"
    purchase_order.db_insert()
    purchase_order.update_children()
    validate_params_from_available_stock("Available Purchased", purchase_order.name)


def test_params_validate_from_available_stock_available_actual_raises_on_no_stock_balance():
    with pytest.raises(ValidationError, match="No Items in Available Actual stock"):
        validate_params_from_available_stock("Available Actual", None)


def test_params_validate_from_available_stock_available_actual_passes(
    monkeypatch: pytest.MonkeyPatch,
):
    patch_get_stock_balance(monkeypatch, {"10014030": 1})
    validate_params_from_available_stock("Available Actual", None)


def test_calculate_commission_and_margin_items_cost_set(sales_order: SalesOrder):
    sales_order.insert()
    resp = calculate_commission_and_margin(sales_order.as_json())
    sales_order._calculate_commission()
    sales_order._calculate_margin()
    assert resp["commission"] == sales_order.commission
    assert resp["margin"] == sales_order.margin


def test_calculate_commission_and_margin_items_cost_not_set(sales_order: SalesOrder):
    sales_order.insert()
    sales_order.commission = sales_order.margin = 0
    sales_order.items_cost = 0
    resp = calculate_commission_and_margin(sales_order.as_json())
    assert resp["commission"] == 0
    assert resp["margin"] == 0
