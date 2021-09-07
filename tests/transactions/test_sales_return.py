from __future__ import annotations

from copy import copy
from typing import Counter

import pytest

import frappe
from comfort import count_quantity, group_by_attr
from comfort.finance import create_payment, get_account
from comfort.finance.doctype.gl_entry.gl_entry import GLEntry
from comfort.stock.doctype.stock_entry.stock_entry import StockEntry
from comfort.transactions.doctype.sales_order.sales_order import SalesOrder
from comfort.transactions.doctype.sales_return.sales_return import (
    SalesReturn,
    _add_rates_to_child_items,
)


def test_sales_return_voucher_property(sales_return: SalesReturn):
    assert type(sales_return._voucher) == SalesOrder
    assert sales_return._voucher.name == sales_return.sales_order


def test_sales_return_delete_empty_items(sales_return: SalesReturn):
    sales_return.append("items", {"qty": 0})
    sales_return.delete_empty_items()
    c: Counter[str] = Counter()
    for i in sales_return.items:
        c[i.item_code] += i.qty
    for qty in c.values():
        assert qty > 0


def test_sales_return_delete_empty_items_no_attr(sales_return: SalesReturn):
    del sales_return.items
    sales_return.delete_empty_items()


def test_sales_return_delete_empty_items_attr_is_none(sales_return: SalesReturn):
    sales_return.items = None
    sales_return.delete_empty_items()


def test_validate_not_all_items_returned_not_raises(sales_return: SalesReturn):
    sales_return._validate_not_all_items_returned()


def test_validate_not_all_items_returned_raises(sales_return: SalesReturn):
    sales_return.add_items(sales_return.get_items_available_to_add())
    with pytest.raises(
        frappe.ValidationError, match="Can't return all items in Sales Order"
    ):
        sales_return._validate_not_all_items_returned()


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


def test_calculate_item_values(sales_return: SalesReturn):
    sales_return._calculate_item_values()
    for item in sales_return.items:
        assert item.amount == item.qty * item.rate


@pytest.mark.parametrize(
    ("paid_amount", "exp_returned_paid_amount"),
    (
        (27370, 2150),  # Fully paid
        (0, 0),  # Not paid
        (100, 0),  # Partially paid but not enough to return
        (26000, 780),
    ),  # Partially paid need to return some
)
def test_calculate_returned_paid_amount(
    sales_return: SalesReturn, paid_amount: int, exp_returned_paid_amount: int
):
    sales_return._voucher._set_paid_and_pending_per_amount()
    if paid_amount > 0:
        sales_return._voucher.add_payment(paid_amount, True)
    sales_return._calculate_returned_paid_amount()
    assert sales_return.returned_paid_amount == exp_returned_paid_amount


def test_get_remaining_qtys(sales_return: SalesReturn):
    items_in_order = sales_return._voucher._get_items_with_splitted_combinations()
    in_order = count_quantity(items_in_order)
    in_return = count_quantity(sales_return.items)

    for item_code, qty in sales_return._get_remaining_qtys(items_in_order):
        assert qty > 0
        if qty > 0:
            assert qty == in_order[item_code] - in_return.get(item_code, 0)


def test_get_items_available_to_add(sales_return: SalesReturn):
    available_item_and_qty = dict(
        sales_return._get_remaining_qtys(
            sales_return._voucher._get_items_with_splitted_combinations()
        )
    )
    for item in sales_return.get_items_available_to_add():
        assert (item["item_name"], item["rate"]) == frappe.get_value(
            "Item", item["item_code"], ("item_name", "rate")
        )
        assert item["qty"] == available_item_and_qty[item["item_code"]]


@pytest.mark.parametrize(
    ("item_code", "qty"),
    (("invalid_item_code", 10), ("40366634", 0), ("40366634", 3)),
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


def test_add_items_not_raises(sales_return: SalesReturn):
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

    prev_qty_counter = count_quantity(sales_return._voucher.items)
    sales_return._split_combinations_in_voucher()
    new_qty_counter = count_quantity(sales_return._voucher.items)
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
    sales_return._voucher.merge_same_items()
    sales_return._voucher.set_child_items()

    counter_before = count_quantity(
        sales_return._voucher._get_items_with_splitted_combinations()
    )
    sales_return._split_combinations_in_voucher()
    counter_after = count_quantity(sales_return._voucher.items)
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


def test_modify_voucher(sales_return: SalesReturn):
    prev_qty_counter = count_quantity(
        sales_return._voucher._get_items_with_splitted_combinations()
    )
    sales_return._modify_voucher()
    new_qty_counter = count_quantity(
        sales_return._voucher._get_items_with_splitted_combinations()
    )

    diff = prev_qty_counter.copy()
    for item_code in prev_qty_counter:
        diff[item_code] -= new_qty_counter[item_code]
        if diff[item_code] == 0:
            del diff[item_code]

    assert diff == count_quantity(sales_return.items)


def test_modify_and_save_voucher(sales_return: SalesReturn):
    sales_return._voucher.docstatus = 1
    sales_return._voucher.db_update_all()
    sales_return._modify_and_save_voucher()


def test_make_delivery_gl_entries_create(sales_return: SalesReturn):
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


def test_make_delivery_gl_entries_not_create(sales_return: SalesReturn):
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
def test_make_stock_entries_create(
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
    return_counter = count_quantity(sales_return.items)
    entry_with_first_type, entry_with_second_type = False, False

    for name in entry_names:
        doc: StockEntry = frappe.get_doc("Stock Entry", name)
        if doc.stock_type == exp_stock_types[0]:
            entry_with_first_type = True
        elif doc.stock_type == exp_stock_types[1]:
            entry_with_second_type = True

        assert count_quantity(doc.items) == return_counter

    assert entry_with_first_type
    assert entry_with_second_type


def test_make_stock_entries_not_create(sales_return: SalesReturn):
    sales_return._voucher.delivery_status = "Some Random Delivery Status"
    sales_return.db_insert()
    sales_return._make_stock_entries()
    assert not frappe.db.exists(
        "Stock Entry",
        {"voucher_type": sales_return.doctype, "voucher_no": sales_return.name},
    )


@pytest.mark.parametrize(
    ("paid_with_cash", "exp_asset_account"),
    ((True, "cash"), (False, "bank"), (None, "bank")),
)
def test_make_payment_gl_entries_create(
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


def test_make_payment_gl_entries_not_create(sales_return: SalesReturn):
    sales_return.returned_paid_amount = 0
    sales_return.db_insert()
    sales_return._make_payment_gl_entries()
    assert not frappe.db.exists(
        "GL Entry",
        {"voucher_type": sales_return.doctype, "voucher_no": sales_return.name},
    )


def test_before_cancel(sales_return: SalesReturn):
    with pytest.raises(
        frappe.ValidationError, match="Not allowed to cancel Sales Return"
    ):
        sales_return.before_cancel()


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
