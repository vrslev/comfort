from __future__ import annotations

from typing import Any

import pytest

from comfort import TypedDocument, get_all, get_doc, get_value
from comfort.finance import GLEntry, Payment
from comfort.finance.utils import cancel_gl_entries_for, get_account
from comfort.transactions import PurchaseOrder, SalesOrder
from frappe import ValidationError


@pytest.mark.parametrize("amount", (0, -10))
def test_payment_validate_raises(payment_sales: Payment, amount: int):
    payment_sales.amount = amount
    with pytest.raises(ValidationError, match="Amount should be more that zero"):
        payment_sales.validate()


@pytest.mark.parametrize("amount", (0.5, 1000))
def test_payment_validate_passes(payment_sales: Payment, amount: Any):
    payment_sales.amount = amount
    payment_sales.validate()


@pytest.mark.parametrize(("v", "expected"), ((True, "cash"), (False, "bank")))
def test_resolve_cash_or_bank(payment_sales: Payment, v: bool, expected: str):
    payment_sales.paid_with_cash = v
    assert payment_sales._resolve_cash_or_bank() == expected


def get_gl_entries(doc: TypedDocument):
    return get_all(
        GLEntry,
        field=("account", "debit", "credit"),
        filter={"voucher_type": doc.doctype, "voucher_no": doc.name},
    )


@pytest.mark.parametrize("cash", (True, False))
def test_payment_create_sales_gl_entries(payment_sales: Payment, cash: bool):
    payment_sales.paid_with_cash = cash
    payment_sales.db_insert()
    payment_sales.create_sales_gl_entries()

    prepaid_sales = get_account("prepaid_sales")
    cash_or_bank = get_account(payment_sales._resolve_cash_or_bank())
    entries = get_gl_entries(payment_sales)
    assert len(entries) == 2

    for entry in entries:
        assert entry.account in (cash_or_bank, prepaid_sales)
        if entry.account == cash_or_bank:
            assert entry.debit == payment_sales.amount
            assert entry.credit == 0
        elif entry.account == prepaid_sales:
            assert entry.debit == 0
            assert entry.credit == payment_sales.amount


@pytest.mark.parametrize(
    (
        "sales_orders_cost",
        "items_to_sell_cost",
        "delivery_cost",
        "exp_prepaid_inventory",
        "exp_purchase_delivery",
    ),
    ((10050, 3130, 5399, 13180, 5399), (10050, 3130, 0, 13180, 0)),
)
def test_create_purchase_gl_entries(
    payment_purchase: Payment,
    purchase_order: PurchaseOrder,
    sales_orders_cost: int,
    items_to_sell_cost: int,
    delivery_cost: int,
    exp_prepaid_inventory: int,
    exp_purchase_delivery: int,
):
    purchase_order.sales_orders_cost = sales_orders_cost
    purchase_order.items_to_sell_cost = items_to_sell_cost
    purchase_order.delivery_cost = delivery_cost
    purchase_order.db_update()

    payment_purchase.paid_with_cash = False
    payment_purchase.db_insert()
    payment_purchase.create_purchase_gl_entries()

    bank = 0
    prepaid_inventory = 0
    purchase_delivery = 0

    for entry in get_gl_entries(payment_purchase):
        if entry.account == get_account("bank"):
            bank += entry.debit - entry.credit
        elif entry.account == get_account("prepaid_inventory"):
            prepaid_inventory += entry.debit - entry.credit
        elif entry.account == get_account("purchase_delivery"):
            purchase_delivery += entry.debit - entry.credit

    assert bank == -(exp_prepaid_inventory + exp_purchase_delivery)
    assert prepaid_inventory == exp_prepaid_inventory
    assert purchase_delivery == purchase_delivery


@pytest.mark.parametrize("docstatus", (0, 1))
def test_set_status_in_sales_order(sales_order: SalesOrder, docstatus: int):
    sales_order.docstatus = docstatus
    sales_order.update_items_from_db()
    sales_order.calculate()
    sales_order.db_insert()
    sales_order.db_update_all()
    sales_order.add_payment(300, cash=True)

    payment_name: str = get_value(
        "Payment", {"voucher_type": sales_order.doctype, "voucher_no": sales_order.name}
    )
    payment = get_doc(Payment, payment_name)
    cancel_gl_entries_for(payment.doctype, payment.name)
    payment.set_status_in_sales_order()

    sales_order.reload()
    assert sales_order.paid_amount == 0
    assert sales_order.payment_status == "Unpaid"
