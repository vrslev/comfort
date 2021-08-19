from __future__ import annotations

from collections import Counter

import pytest

import frappe
from comfort import count_quantity
from comfort.comfort_core.doctype.commission_settings.commission_settings import (
    CommissionSettings,
)
from comfort.entities.doctype.item.item import Item
from comfort.finance.doctype.payment.payment import Payment
from comfort.transactions.doctype.purchase_order.purchase_order import PurchaseOrder
from comfort.transactions.doctype.sales_order.sales_order import SalesOrder

#############################
#     SalesOrderMethods     #
#############################


def test_merge_same_items(sales_order: SalesOrder):  # TODO: test not messed up
    item = sales_order.items[0].as_dict().copy()
    item.qty = 4
    second_item = sales_order.items[1].as_dict().copy()
    second_item.qty = 2
    sales_order.extend("items", [item, second_item])

    sales_order.merge_same_items()
    c: Counter[str] = Counter()
    for item in sales_order.items:
        c[item.item_code] += 1

    assert len(sales_order.items) == 2
    assert all(c == 1 for c in c.values())


def test_delete_empty_items(sales_order: SalesOrder):
    sales_order.append("items", {"qty": 0})
    sales_order.delete_empty_items()

    c: Counter[str] = Counter()
    for i in sales_order.items:
        c[i.item_code] += i.qty

    for qty in c.values():
        assert qty > 0


def test_update_items_from_db(sales_order: SalesOrder):
    sales_order.update_items_from_db()

    for i in sales_order.items:
        doc: Item = frappe.get_doc("Item", i.item_code)
        assert i.item_name == doc.item_name
        assert i.rate == doc.rate
        assert i.weight == doc.weight
        assert i.amount == doc.rate * i.qty
        assert i.total_weight == doc.weight * i.qty


def test_set_child_items_not_set_if_no_items(sales_order: SalesOrder):
    sales_order.items = []
    sales_order.set_child_items()
    assert not sales_order.child_items


def test_set_child_items(sales_order: SalesOrder, item: Item):
    sales_order.set_child_items()

    item_code_qty_pairs = count_quantity(sales_order.child_items).items()
    exp_item_code_qty_pairs = count_quantity(item.child_items).items()

    for p in exp_item_code_qty_pairs:
        assert p in item_code_qty_pairs


def test_calculate_item_totals(sales_order: SalesOrder):
    sales_order.update_items_from_db()

    exp_total_quantity, exp_total_weight, exp_items_cost = 0, 0.0, 0
    for i in sales_order.items:
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


def test_calculate_commission_no_edit_commission(
    sales_order: SalesOrder, commission_settings: CommissionSettings
):
    commission_settings.insert()

    sales_order.items_cost = 5309
    sales_order._calculate_commission()

    assert sales_order.commission == CommissionSettings.get_commission_percentage(
        sales_order.items_cost
    )


def test_calculate_commission_with_edit_commission(
    sales_order: SalesOrder, commission_settings: CommissionSettings
):
    commission_settings.insert()

    sales_order.edit_commission = True
    sales_order.commission = 100
    sales_order.items_cost = 21094
    sales_order._calculate_commission()

    assert sales_order.commission == 100


def test_calculate_margin_zero_if_items_cost_is_zero(sales_order: SalesOrder):
    sales_order.items_cost = 0
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


#############################
#    SalesOrderStatuses     #
#############################


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
    Payment.create_for(sales_order.doctype, sales_order.name, paid_amount, True)

    sales_order.total_amount = total_amount
    sales_order._set_paid_and_pending_per_amount()

    assert sales_order.paid_amount == paid_amount
    assert sales_order.per_paid == exp_per_paid
    assert sales_order.pending_amount == exp_pending_amount


def test_set_paid_and_pending_per_amount_with_zero_total_amount(
    sales_order: SalesOrder,
):
    sales_order.total_amount = 0
    sales_order._set_paid_and_pending_per_amount()

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


def test_set_delivery_status(sales_order: SalesOrder, purchase_order: PurchaseOrder):
    sales_order._set_delivery_status


@pytest.mark.parametrize(
    "docstatus,payment_status,delivery_status,expected_status",
    (
        (0, None, None, "Draft"),
        (1, "Paid", "Delivered", "Completed"),
        (1, None, None, "In Progress"),
        (2, None, None, "Cancelled"),
    ),
)
def test_set_document_status(
    sales_order: SalesOrder,
    docstatus: int,
    payment_status: str,
    delivery_status: str,
    expected_status: str,
):
    sales_order.docstatus = docstatus
    sales_order.payment_status = payment_status
    sales_order.delivery_status = delivery_status
    sales_order._set_document_status()
    assert sales_order.status == expected_status


# def _validate_and_set_status_before_add_receipt(): ... # TODO: When Purchase Order
