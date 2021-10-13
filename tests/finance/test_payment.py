from __future__ import annotations

import pytest

from comfort import get_all, get_doc, get_value
from comfort.finance import get_account
from comfort.finance.doctype.gl_entry.gl_entry import GLEntry
from comfort.finance.doctype.payment.payment import Payment
from comfort.transactions.doctype.purchase_order.purchase_order import PurchaseOrder
from comfort.transactions.doctype.sales_order.sales_order import SalesOrder
from frappe import ValidationError


@pytest.mark.parametrize("amount", (0, -10))
def test_payment_validate_raises(payment_sales: Payment, amount: int):
    payment_sales.amount = amount
    with pytest.raises(ValidationError, match="Amount should be more that zero"):
        payment_sales.validate()


@pytest.mark.parametrize("amount", (0.5, 1000))
def test_payment_validate_not_raises(payment_sales: Payment, amount: float | int):
    payment_sales.amount = amount  # type: ignore
    payment_sales.validate()


def test_new_gl_entry(payment_sales: Payment):
    account, debit, credit = "cash", 300, 0
    payment_sales.db_insert()
    payment_sales._new_gl_entry(account, debit, credit)

    values: tuple[str, int, int] = get_value(
        "GL Entry",
        filters={
            "voucher_type": payment_sales.doctype,
            "voucher_no": payment_sales.name,
        },
        fieldname=("account", "debit", "credit"),
    )

    assert get_account(account) == values[0]
    assert debit == values[1]
    assert credit == values[2]


@pytest.mark.parametrize(
    "paid_with_cash,expected_account", ((True, "cash"), (False, "bank"))
)
def test_resolve_cash_or_bank(
    payment_sales: Payment, paid_with_cash: bool, expected_account: str
):
    payment_sales.paid_with_cash = paid_with_cash
    assert payment_sales._resolve_cash_or_bank() == expected_account


def test_get_amounts_for_sales_gl_entries(
    payment_sales: Payment, sales_order: SalesOrder
):
    sales_order.total_amount = 10000
    sales_order.service_amount = 800
    sales_order.db_update_all()
    amounts = payment_sales._get_amounts_for_sales_gl_entries()

    assert amounts["sales_amount"] == 9200
    assert amounts["delivery_amount"] == 300
    assert amounts["installation_amount"] == 500


def get_gl_entries(doc: Payment | SalesOrder):
    return get_all(
        GLEntry,
        fields=("account", "debit", "credit"),
        filters={"voucher_type": doc.doctype, "voucher_no": doc.name},
    )


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
    payment_sales: Payment,
    sales_order: SalesOrder,
    paid_amount: int,
    exp_sales_amount: int,
    exp_delivery_amount: int,
    exp_installation_amount: int,
):
    sales_order.total_amount = 5800
    sales_order.service_amount = 800
    sales_order.db_update_all()

    payment_sales.amount = paid_amount
    payment_sales.db_insert()
    payment_sales._create_categories_sales_gl_entries(
        **payment_sales._get_amounts_for_sales_gl_entries()
    )

    amounts = {"sales": 0, "delivery": 0, "installation": 0}

    for entry in get_gl_entries(payment_sales):
        for account_name in amounts:
            if get_account(account_name) == entry.account:
                amounts[account_name] += entry.credit

    assert amounts["sales"] == exp_sales_amount
    assert amounts["delivery"] == exp_delivery_amount
    assert amounts["installation"] == exp_installation_amount


def test_create_categories_sales_gl_entries_skips_on_zero_fund_amount(
    payment_sales: Payment,
    sales_order: SalesOrder,
):
    payment_sales.amount = 500
    payment_sales.db_insert()
    payment_sales._create_categories_sales_gl_entries(0, 300, 200)
    accounts = [entry.account for entry in get_gl_entries(sales_order)]
    assert get_account("sales") not in accounts


def test_create_income_sales_gl_entry(payment_sales: Payment):
    payment_sales.amount = 5000
    payment_sales.db_insert()
    payment_sales._create_income_sales_gl_entry()

    amount = 0
    for entry in get_gl_entries(payment_sales):
        amount += entry.debit
    assert amount == 5000


@pytest.mark.parametrize(
    (
        "sales_orders_cost",
        "items_to_sell_cost",
        "delivery_cost",
        "exp_prepaid_inventory",
        "exp_purchase_delivery",
    ),
    (
        (10050, 3130, 5399, 13180, 5399),
        (10050, 3130, 0, 13180, 0),
    ),
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
    payment.cancel_gl_entries()
    payment.set_status_in_sales_order()

    sales_order.reload()
    assert sales_order.paid_amount == 0
    assert sales_order.payment_status == "Unpaid"
