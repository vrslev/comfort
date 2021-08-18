from __future__ import annotations

from collections import Counter
from typing import TYPE_CHECKING, Any

import pytest

import frappe
from comfort import count_quantity
from comfort.comfort_core.doctype.commission_settings.commission_settings import (
    CommissionSettings,
)
from comfort.entities.doctype.customer.customer import Customer
from comfort.entities.doctype.item.item import Item
from comfort.finance import get_account
from comfort.finance.doctype.gl_entry.gl_entry import GLEntry
from comfort.stock.doctype.bin.bin import Bin
from comfort.transactions.doctype.sales_order.sales_order import SalesOrder
from frappe import ValidationError

if not TYPE_CHECKING:
    from tests.comfort_core.test_commission_settings import commission_settings
    from tests.entities.test_customer import customer
    from tests.entities.test_item import child_items, item


@pytest.fixture
def sales_order(customer: Customer, child_items: list[Item], item: Item):
    customer.insert()
    item.insert()

    doc: SalesOrder = frappe.get_doc(
        {
            "name": "SO-2021-0001",
            "customer": "Pavel Durov",
            "edit_commission": 0,
            "discount": 0,
            "paid_amount": 0,
            "doctype": "Sales Order",
            "services": [
                {
                    "type": "Delivery to Entrance",
                    "rate": 300,
                },
                {
                    "type": "Installation",
                    "rate": 500,
                },
            ],
        }
    )
    doc.extend(
        "items",
        [
            {"item_code": item.item_code, "qty": 1},
            {"item_code": child_items[0].item_code, "qty": 2},
        ],
    )
    return doc


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
    sales_order._update_items_from_db()

    for i in sales_order.items:
        doc: Item = frappe.get_doc("Item", i.item_code)
        assert i.item_name == doc.item_name
        assert i.rate == doc.rate
        assert i.weight == doc.weight
        assert i.amount == doc.rate * i.qty
        assert i.total_weight == doc.weight * i.qty


def test_calculate_item_totals(sales_order: SalesOrder):
    sales_order._update_items_from_db()

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


@pytest.mark.parametrize(
    "total_amount,paid_amount,exp_per_paid,exp_pending_amount",
    ((0, 0, 100.0, 0), (500, 250, 50.0, 250)),
)
def test_set_paid_and_pending_per_amount(
    sales_order: SalesOrder,
    total_amount: int,
    paid_amount: int,
    exp_per_paid: float,
    exp_pending_amount: int,
):
    sales_order.db_insert()
    GLEntry.new(sales_order, get_account("cash"), paid_amount, 0)

    sales_order.total_amount = total_amount
    sales_order._set_paid_and_pending_per_amount()

    assert sales_order.paid_amount == paid_amount
    assert sales_order.per_paid == exp_per_paid
    assert sales_order.pending_amount == exp_pending_amount


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


#############################
#     SalesOrderFinance     #
#############################


def get_gl_entries(doc: SalesOrder) -> list[GLEntry]:
    return frappe.get_all(
        "GL Entry",
        fields=["account", "debit", "credit"],
        filters={"voucher_type": doc.doctype, "voucher_no": doc.name},
    )


def test_get_amounts_for_invoice_gl_entries(sales_order: SalesOrder):
    sales_order.total_amount = 10000
    sales_order.service_amount = 800
    amounts = sales_order._get_amounts_for_invoice_gl_entries()

    assert amounts["sales_amount"] == 9200
    assert amounts["delivery_amount"] == 300
    assert amounts["installation_amount"] == 500


@pytest.mark.parametrize(
    "paid_amount,exp_sales_amount,exp_delivery_amount,exp_installation_amount",
    (
        (500, 500, 0, 0),
        (5000, 5000, 0, 0),
        (5200, 5000, 200, 0),
        (5400, 5000, 300, 100),
        (5800, 5000, 300, 500),
        (5900, 5100, 300, 500),
    ),
)
def test_make_categories_invoice_gl_entries(
    sales_order: SalesOrder,
    paid_amount: int,
    exp_sales_amount: int,
    exp_delivery_amount: int,
    exp_installation_amount: int,
):
    sales_order.total_amount = 5800
    sales_order.service_amount = 800
    sales_order.db_insert()

    sales_order._make_categories_invoice_gl_entries(
        paid_amount, **sales_order._get_amounts_for_invoice_gl_entries()
    )

    amounts = {"sales": 0, "delivery": 0, "installation": 0}

    for entry in get_gl_entries(sales_order):
        for account_name in amounts:
            if get_account(account_name) == entry.account:
                amounts[account_name] += entry.credit

    assert amounts["sales"] == exp_sales_amount
    assert amounts["delivery"] == exp_delivery_amount
    assert amounts["installation"] == exp_installation_amount


def test_make_categories_invoice_gl_entries_skips_on_zero_fund_amount(
    sales_order: SalesOrder,
):
    sales_order.db_insert()
    sales_order._make_categories_invoice_gl_entries(500, 0, 300, 200)
    accounts = [entry.account for entry in get_gl_entries(sales_order)]
    assert get_account("sales") not in accounts


@pytest.mark.parametrize(
    "paid_with_cash,expected_account", ((True, "cash"), (False, "bank"))
)
def test_make_income_invoice_gl_entry(
    sales_order: SalesOrder, paid_with_cash: bool, expected_account: str
):
    sales_order.db_insert()
    sales_order._make_income_invoice_gl_entry(5000, paid_with_cash)

    amount = 0
    for entry in get_gl_entries(sales_order):
        assert entry.account == get_account(expected_account)
        amount += entry.debit
    assert amount == 5000


def test_make_invoice_gl_entries_raises_on_zero_paid_amount(sales_order: SalesOrder):
    with pytest.raises(ValidationError, match="Paid Amount should be more that zero"):
        sales_order.make_invoice_gl_entries(0, True)


def test_make_invoice_gl_entries_raises_on_zero_total_amount(sales_order: SalesOrder):
    sales_order.total_amount = 0
    with pytest.raises(ValidationError, match="Total Amount should be more that zero"):
        sales_order.make_invoice_gl_entries(100, True)


def test_make_delivery_gl_entries(sales_order: SalesOrder):
    items_cost = 5000

    sales_order.items_cost = items_cost
    sales_order.delivery_status = "Delivered"
    sales_order.db_insert()
    sales_order.make_delivery_gl_entries()

    for entry in get_gl_entries(sales_order):
        if get_account("inventory") == entry.account:
            assert entry.credit == items_cost
        elif get_account("cost_of_goods_sold") == entry.account:
            assert entry.debit == items_cost


def test_make_delivery_gl_entries_raises_on_wrong_delivery_status(
    sales_order: SalesOrder,
):
    sales_order.delivery_status = "To Deliver"
    sales_order.db_insert()
    with pytest.raises(
        ValidationError, match='Cannot make GL Entries when status is not "Delivered"'
    ):
        sales_order.make_delivery_gl_entries()


#############################
#      SalesOrderStock      #
#############################


def test_get_items_with_splitted_combinations(sales_order: SalesOrder):
    sales_order.set_child_items()
    items = sales_order._get_items_with_splitted_combinations()
    parents: set[Any] = set()
    for child in sales_order.child_items:
        assert child in items
        parents.add(child.parent_item_code)

    for i in sales_order.items:
        if i.item_code in parents:
            assert i not in items
        else:
            assert i in items


def test_remove_items_from_reserved_actual(sales_order: SalesOrder):
    sales_order.set_child_items()
    items = sales_order._get_items_with_splitted_combinations()
    for i in items:
        Bin.update_for(i.item_code, reserved_actual=i.qty)
    sales_order.remove_items_from_reserved_actual()
    for i in items:
        assert frappe.get_value("Bin", i.item_code, "reserved_actual") == 0


#############################
#    SalesOrderStatuses     #
#############################


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


# def test_set_delivery_status(sales_order: SalesOrder): TODO: When Purchase Order
#     sales_order._set_delivery_status


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


# def _set_validate_and_set_status_before_set_delivered(): ... # TODO: When Purchase Order
