from __future__ import annotations

from copy import copy

import pytest

import frappe
from comfort import count_qty
from comfort.finance import create_payment, get_account
from comfort.finance.doctype.gl_entry.gl_entry import GLEntry
from comfort.stock.doctype.stock_entry.stock_entry import StockEntry
from comfort.transactions import merge_same_items
from comfort.transactions.doctype.sales_order.sales_order import SalesOrder
from comfort.transactions.doctype.sales_return.sales_return import SalesReturn
from tests.stock.test_init import reverse_qtys


def test_sales_return_voucher_property(sales_return: SalesReturn):
    assert type(sales_return._voucher) == SalesOrder
    assert sales_return._voucher.name == sales_return.sales_order


@pytest.mark.parametrize(
    ("paid_amount", "exp_returned_paid_amount"),
    (
        (27370, 2150),  # Fully paid
        (0, 0),  # Not paid
        (100, 0),  # Partially paid but not enough to return
        (26000, 780),
    ),  # Partially paid need to return some
)
def test_sales_return_calculate_returned_paid_amount(
    sales_return: SalesReturn, paid_amount: int, exp_returned_paid_amount: int
):
    sales_return._voucher._set_paid_and_pending_per_amount()
    if paid_amount > 0:
        sales_return._voucher.add_payment(paid_amount, True)
    sales_return._calculate_returned_paid_amount()
    assert sales_return.returned_paid_amount == exp_returned_paid_amount


def test_validate_voucher_statuses_docstatus_not_raises(sales_return: SalesReturn):
    sales_return._voucher.docstatus = 1
    sales_return._voucher.delivery_status = "Purchased"
    sales_return._validate_voucher_statuses()


@pytest.mark.parametrize("docstatus", (0, 2))
def test_validate_voucher_statuses_docstatus_raises(
    sales_return: SalesReturn, docstatus: int
):
    sales_return._voucher.docstatus = docstatus
    sales_return._voucher.delivery_status = "Purchased"
    with pytest.raises(frappe.ValidationError, match="Sales Order should be submitted"):
        sales_return._validate_voucher_statuses()


@pytest.mark.parametrize("delivery_status", ("Purchased", "To Deliver", "Delivered"))
def test_validate_voucher_statuses_delivery_status_not_raises(
    sales_return: SalesReturn, delivery_status: str
):
    sales_return._voucher.docstatus = 1
    sales_return._voucher.delivery_status = delivery_status
    sales_return._validate_voucher_statuses()


@pytest.mark.parametrize("delivery_status", ("", "To Purchase", "Some Random Status"))
def test_validate_voucher_statuses_delivery_status_raises(
    sales_return: SalesReturn, delivery_status: str
):
    sales_return._voucher.docstatus = 1
    sales_return._voucher.delivery_status = delivery_status
    with pytest.raises(
        frappe.ValidationError,
        match="Delivery Status should be Purchased, To Deliver or Delivered",
    ):
        sales_return._validate_voucher_statuses()


def generate_items_from_counter(counter: dict[str, int]):
    return [{"item_code": item_code, "qty": qty} for item_code, qty in counter.items()]


@pytest.mark.parametrize(
    ("items_counter", "child_items_counter", "sales_return_counter"),
    # "29128569" is combination
    (
        # No `child_items` to iterate in
        ({"29128569": 1}, {}, {"10014030": 2}),
        # Item in `child_items` and in `items` but there's enough
        # quantity in `items` to not mess up Order with split
        (
            {"29128569": 1, "10014030": 5},
            {"10014030": 20, "10366598": 1},
            {"10014030": 3},
        ),
    ),
)
def test_split_combinations_in_voucher_not_needed(
    sales_return: SalesReturn,
    items_counter: dict[str, int],
    child_items_counter: dict[str, int],
    sales_return_counter: dict[str, int],
):

    sales_return._voucher.items = []
    sales_return._voucher.child_items = []
    sales_return.items = []

    sales_return._voucher.extend("items", generate_items_from_counter(items_counter))
    sales_return._voucher.extend(
        "child_items", generate_items_from_counter(child_items_counter)
    )
    sales_return.extend("items", generate_items_from_counter(sales_return_counter))

    prev_qty_counter = count_qty(sales_return._voucher.items)
    sales_return._split_combinations_in_voucher()
    new_qty_counter = count_qty(sales_return._voucher.items)
    assert prev_qty_counter == new_qty_counter


@pytest.mark.parametrize(
    ("items_counter", "sales_return_counter"),
    (
        # Item in `child_items` and in `items` but there's enough
        # quantity in `items` to not mess up Order with split
        ({"29128569": 1, "10014030": 1}, {"10014030": 3}),
        # Item in child items and not in items
        ({"29128569": 1}, {"10014030": 3}),
    ),
)
def test_split_combinations_in_voucher_needed(
    sales_return: SalesReturn,
    items_counter: dict[str, int],
    sales_return_counter: dict[str, int],
):
    sales_return.items = []
    sales_return.extend("items", generate_items_from_counter(sales_return_counter))

    sales_return._voucher.items = []
    sales_return._voucher.extend("items", generate_items_from_counter(items_counter))
    sales_return._voucher.items = merge_same_items(sales_return._voucher.items)
    sales_return._voucher.set_child_items()

    counter_before = count_qty(
        sales_return._voucher._get_items_with_splitted_combinations()
    )
    sales_return._split_combinations_in_voucher()
    counter_after = count_qty(sales_return._voucher.items)
    assert counter_before == counter_after


def test_add_missing_info_to_items_in_voucher(sales_return: SalesReturn):
    for item in sales_return._voucher.items:
        item.rate = None
        item.weight = None

    sales_return._add_missing_info_to_items_in_voucher()

    for item in sales_return._voucher.items:
        res: tuple[str, int, int] = frappe.get_value(
            "Item", item.item_code, ("item_name", "rate", "weight")
        )
        assert item.item_name == res[0]
        assert item.rate == res[1]
        assert item.weight == res[2]


def test_sales_return_modify_voucher(sales_return: SalesReturn):
    prev_qty_counter = count_qty(
        sales_return._voucher._get_items_with_splitted_combinations()
    )
    sales_return._modify_voucher()
    new_qty_counter = count_qty(
        sales_return._voucher._get_items_with_splitted_combinations()
    )

    diff = prev_qty_counter.copy()
    for item_code in prev_qty_counter:
        diff[item_code] -= new_qty_counter[item_code]
        if diff[item_code] == 0:
            del diff[item_code]

    assert diff == count_qty(sales_return.items)


def test_modify_and_save_voucher(sales_return: SalesReturn):
    sales_return._voucher.docstatus = 1
    sales_return._voucher.db_update_all()
    sales_return._modify_and_save_voucher()


def test_sales_return_make_delivery_gl_entries_create(sales_return: SalesReturn):
    sales_return._voucher.delivery_status = "Delivered"
    sales_return.db_insert()
    sales_return._make_delivery_gl_entries()
    prev_items_cost = copy(sales_return._voucher.items_cost)
    sales_return._modify_voucher()
    new_items_cost = copy(sales_return._voucher.items_cost)
    amount = prev_items_cost - new_items_cost
    entries: list[GLEntry] = frappe.get_all(
        "GL Entry",
        fields=("account", "debit", "credit"),
        filters={
            "voucher_type": sales_return.doctype,
            "voucher_no": sales_return.name,
        },
    )
    assert len(entries) == 2
    accounts = get_account("cost_of_goods_sold"), get_account("inventory")
    for entry in entries:
        assert entry.account in accounts
        if entry.account == accounts[0]:
            assert entry.debit == 0
            assert entry.credit == amount
        elif entry.account == accounts[1]:
            assert entry.debit == amount
            assert entry.credit == 0


def test_sales_return_make_delivery_gl_entries_not_create(sales_return: SalesReturn):
    sales_return._voucher.delivery_status = "Random Delivery Status"
    sales_return.db_insert()
    sales_return._make_delivery_gl_entries()
    assert not frappe.db.exists(
        "GL Entry",
        {"voucher_type": sales_return.doctype, "voucher_no": sales_return.name},
    )


@pytest.mark.parametrize(
    ("delivery_status", "exp_stock_types"),
    (
        ("Purchased", ("Reserved Purchased", "Available Purchased")),
        ("To Deliver", ("Reserved Actual", "Available Actual")),
        ("Delivered", ("Reserved Actual", "Available Actual")),
    ),
)
def test_sales_return_make_stock_entries_create(
    sales_return: SalesReturn, delivery_status: str, exp_stock_types: tuple[str, str]
):
    sales_return._voucher.delivery_status = delivery_status
    sales_return.db_insert()
    sales_return._make_stock_entries()

    entry_names: list[str] = [
        e.name
        for e in frappe.get_all(
            "Stock Entry",
            {
                "voucher_type": sales_return.doctype,
                "voucher_no": sales_return.name,
            },
        )
    ]
    assert len(entry_names) == 2
    return_counter = count_qty(sales_return.items)
    entry_with_first_type, entry_with_second_type = False, False

    for name in entry_names:
        doc: StockEntry = frappe.get_doc("Stock Entry", name)
        expected_counter = return_counter
        if doc.stock_type == exp_stock_types[0]:
            expected_counter = reverse_qtys(return_counter)
            entry_with_first_type = True
        elif doc.stock_type == exp_stock_types[1]:
            entry_with_second_type = True
        assert count_qty(doc.items) == expected_counter

    assert entry_with_first_type
    assert entry_with_second_type


def test_sales_return_make_stock_entries_not_create(sales_return: SalesReturn):
    sales_return._voucher.delivery_status = "Some Random Delivery Status"
    sales_return.db_insert()
    with pytest.raises(KeyError):
        sales_return._make_stock_entries()


@pytest.mark.parametrize(
    ("paid_with_cash", "exp_asset_account"),
    ((True, "cash"), (False, "bank"), (None, "bank")),
)
def test_sales_return_make_payment_gl_entries_create(
    sales_return: SalesReturn, paid_with_cash: bool | None, exp_asset_account: str
):
    sales_return.returned_paid_amount = 1000
    sales_return.db_insert()
    if paid_with_cash is not None:
        create_payment("Sales Order", sales_return.sales_order, 1000, paid_with_cash)
    sales_return._make_payment_gl_entries()
    entries: list[GLEntry] = frappe.get_all(
        "GL Entry",
        fields=("account", "debit", "credit"),
        filters={"voucher_type": sales_return.doctype, "voucher_no": sales_return.name},
    )
    cash_account = get_account("cash")
    bank_account = get_account("bank")
    sales_account = get_account("sales")
    assert len(entries) == 2
    for entry in entries:
        assert entry.account in (cash_account, bank_account, sales_account)
        if entry.account in (cash_account, bank_account):
            assert entry.account == get_account(exp_asset_account)
            assert entry.debit == 0
            assert entry.credit == 1000
        elif entry.account == sales_account:
            assert entry.debit == 1000
            assert entry.credit == 0


def test_sales_return_make_payment_gl_entries_not_create(sales_return: SalesReturn):
    sales_return.returned_paid_amount = 0
    sales_return.db_insert()
    sales_return._make_payment_gl_entries()
    assert not frappe.db.exists(
        "GL Entry",
        {"voucher_type": sales_return.doctype, "voucher_no": sales_return.name},
    )
