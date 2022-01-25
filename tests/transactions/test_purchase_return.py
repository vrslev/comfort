from __future__ import annotations

from collections import Counter
from types import SimpleNamespace
from typing import Generator, Literal

import pytest

import frappe
from comfort import count_qty, get_all, get_doc, get_value, group_by_attr, new_doc
from comfort.entities.doctype.item.item import Item
from comfort.finance import get_account
from comfort.finance.doctype.gl_entry.gl_entry import GLEntry
from comfort.stock.doctype.stock_entry.stock_entry import StockEntry
from comfort.transactions import AnyChildItem, merge_same_items
from comfort.transactions.doctype.purchase_order.purchase_order import PurchaseOrder
from comfort.transactions.doctype.purchase_return.purchase_return import PurchaseReturn
from comfort.transactions.doctype.sales_order.sales_order import SalesOrder
from comfort.transactions.doctype.sales_order_child_item.sales_order_child_item import (
    SalesOrderChildItem,
)
from comfort.transactions.doctype.sales_order_item.sales_order_item import (
    SalesOrderItem,
)
from comfort.transactions.doctype.sales_return.sales_return import SalesReturn
from comfort.transactions.doctype.sales_return_item.sales_return_item import (
    SalesReturnItem,
)


def test_purchase_return_voucher_property(purchase_return: PurchaseReturn):
    assert type(purchase_return._voucher) == PurchaseOrder
    assert purchase_return._voucher.name == purchase_return.purchase_order


def test_purchase_return_calculate_returned_paid_amount(
    purchase_return: PurchaseReturn,
):
    purchase_return._calculate_returned_paid_amount()
    assert purchase_return.returned_paid_amount == sum(
        item.qty * item.rate for item in purchase_return.items
    )


def test_purchase_return_validate_voucher_statuses_docstatus_not_raises(
    purchase_return: PurchaseReturn,
):
    purchase_return._voucher.docstatus = 1
    purchase_return._voucher.status = "To Receive"
    purchase_return._validate_voucher_statuses()


@pytest.mark.parametrize("docstatus", (0, 2))
def test_purchase_return_validate_voucher_statuses_docstatus_raises(
    purchase_return: PurchaseReturn, docstatus: int
):
    purchase_return._voucher.docstatus = docstatus
    with pytest.raises(
        frappe.ValidationError, match="Purchase Order should be submitted"
    ):
        purchase_return._validate_voucher_statuses()


@pytest.mark.parametrize("status", ("To Receive", "Completed"))
def test_purchase_return_validate_voucher_statuses_status_not_raises(
    purchase_return: PurchaseReturn, status: Literal["To Receive", "Completed"]
):
    purchase_return._voucher.docstatus = 1
    purchase_return._voucher.status = status
    purchase_return._validate_voucher_statuses()


@pytest.mark.parametrize("status", ("Draft", "Cancelled", "Some Random Status"))
def test_purchase_return_validate_voucher_statuses_status_raises(
    purchase_return: PurchaseReturn, status: str
):
    purchase_return._voucher.docstatus = 1
    purchase_return._voucher.status = status  # type: ignore
    with pytest.raises(
        frappe.ValidationError, match="Status should be To Receive or Completed"
    ):
        purchase_return._validate_voucher_statuses()


def test_purchase_return_get_all_items(purchase_return: PurchaseReturn, item: Item):
    # Insert cancelled Sales Order
    doc = new_doc(SalesOrder)
    doc.__newname = "test1"  # type: ignore
    doc.customer = purchase_return._voucher.sales_orders[0].customer
    doc.append("items", {"item_code": item.item_code, "qty": 1})
    doc.submit()
    doc.cancel()

    purchase_return._voucher.append("sales_orders", {"sales_order_name": doc.name})
    items = purchase_return._get_all_items()
    exp_items: list[AnyChildItem] = list(
        purchase_return._voucher.get_items_to_sell(True)
    )
    exp_items += purchase_return._voucher.get_items_in_sales_orders(True)
    assert count_qty(items) == count_qty(exp_items)
    can_allocate_items: Generator[bool | None, None, None] = (
        item.get("doctype") and item.get("parent") for item in items
    )
    assert any(can_allocate_items)


def test_allocate_items(purchase_return: PurchaseReturn):
    exp_counters: dict[str | None, Counter[str]] = {
        None: Counter({"10366598": 2, "40366634": 1}),
        purchase_return._voucher.sales_orders[0].sales_order_name: Counter(
            {"10366598": 1}
        ),
    }
    all_items = purchase_return._get_all_items()
    purchase_return._add_missing_fields_to_items(all_items)
    grouped_items = group_by_attr(all_items)
    order_names_with_items = purchase_return._allocate_items().items()
    for order_name, cur_items in order_names_with_items:
        cur_counter = count_qty(SimpleNamespace(**i) for i in cur_items)
        assert cur_counter == exp_counters[order_name]

        for item in cur_items:
            grouped_item = grouped_items[item["item_code"]][0]
            assert item["item_name"] == grouped_item.item_name
            assert item["rate"] == grouped_item.rate  # type: ignore


def test_make_sales_returns_creation(
    purchase_return: PurchaseReturn, sales_order: SalesOrder
):
    sales_order.db_set("docstatus", 1)
    sales_order.db_set("delivery_status", "Purchased")
    sales_order.reload()
    orders_to_items = purchase_return._allocate_items()
    purchase_return._make_sales_returns(orders_to_items)
    sales_returns = get_all(SalesReturn, fields=("name", "sales_order"))
    grouped_sales_returns = group_by_attr(sales_returns, attr="sales_order")

    assert (
        len(sales_returns) == len(orders_to_items) - 1
    )  # There's None for items to sell

    def build_shorten_item(
        item: SalesOrderItem | SalesOrderChildItem | SalesReturnItem | SimpleNamespace,
    ) -> dict[str, str | int | None]:
        return {
            "item_code": item.item_code,
            "item_name": item.item_name,
            "qty": item.qty,
            "rate": item.rate,  # type: ignore
        }

    for order_name, cur_items in orders_to_items.items():
        if order_name is None:
            continue
        doc = get_doc(SalesReturn, grouped_sales_returns[order_name][0].name)
        assert doc.from_purchase_return == purchase_return.name
        assert [build_shorten_item(i) for i in doc.items] == [
            build_shorten_item(SimpleNamespace(**i)) for i in cur_items
        ]
        assert doc.docstatus == 1


def test_make_sales_returns_docstatus_all_items_returns(
    purchase_return: PurchaseReturn,
):
    purchase_return._voucher.items_to_sell = []
    purchase_return._voucher.append(
        "items_to_sell", {"item_code": "10014030", "qty": 2}
    )

    sales_order = get_doc(
        SalesOrder, purchase_return._voucher.sales_orders[0].sales_order_name
    )
    sales_order.items = []
    sales_order.append("items", {"item_code": "10366598", "qty": 1})
    sales_order.submit()
    sales_order.db_set("delivery_status", "Purchased")

    items = purchase_return._voucher.get_items_in_sales_orders(True)
    purchase_return._add_missing_fields_to_items(items)
    purchase_return.items = []
    purchase_return.add_items([dict(i) for i in items])  # type: ignore
    purchase_return.db_insert()
    purchase_return.update_children()

    purchase_return._make_sales_returns(purchase_return._allocate_items())

    assert sales_order.db_get("docstatus") == 2
    assert sales_order.name not in (
        o.sales_order_name for o in purchase_return._voucher.sales_orders
    )


def test_make_sales_returns_docstatus_not_all_items_returns(
    purchase_return: PurchaseReturn,
):
    sales_order = get_doc(
        SalesOrder, purchase_return._voucher.sales_orders[0].sales_order_name
    )
    sales_order.docstatus = 1
    sales_order.delivery_status = "Purchased"
    sales_order.db_update()
    purchase_return._make_sales_returns(purchase_return._allocate_items())
    assert sales_order.db_get("docstatus") == 1
    assert sales_order.name in (
        o.sales_order_name for o in purchase_return._voucher.sales_orders
    )


@pytest.mark.parametrize(
    ("rate", "weight", "item_name", "amount"),
    (
        (None, 100, "The Name", 100),
        (200, None, "The Name", 200),
        (200, 100, None, 200),
        (200, 100, "The Name", None),
        (200, None, "The Name", None),
        (None, None, None, None),
    ),
)
def test_add_missing_field_to_voucher_items_to_sell_changes(
    purchase_return: PurchaseReturn,
    rate: int | None,
    weight: int | None,
    item_name: str | None,
    amount: int | None,
):
    items: list[AnyChildItem] = list(  # type: ignore
        merge_same_items(purchase_return._voucher.get_items_to_sell(True))
    )
    item = items[0]
    item.rate = rate  # type: ignore
    item.weight = weight  # type: ignore
    item.item_name = item_name
    item.amount = amount  # type: ignore
    purchase_return._add_missing_field_to_voucher_items_to_sell(items)
    values: tuple[int, float, str, int] = get_value(
        "Item", item.item_code, ("rate", "weight", "item_name")
    )
    assert item.rate == values[0]  # type: ignore
    assert item.weight == values[1]  # type: ignore
    assert item.item_name == values[2]
    assert item.amount == item.qty * item.rate  # type: ignore


def test_add_missing_field_to_voucher_items_to_sell_not_changes(
    purchase_return: PurchaseReturn,
):
    rate, weight, item_name, amount = 100, 200, "The Name", 345
    items: list[AnyChildItem] = list(  # type: ignore
        merge_same_items(purchase_return._voucher.get_items_to_sell(True))
    )
    item = items[0]
    item.rate = rate  # type: ignore
    item.weight = weight  # type: ignore
    item.item_name = item_name
    item.amount = amount  # type: ignore
    purchase_return._add_missing_field_to_voucher_items_to_sell(items)
    assert item.rate == rate  # type: ignore
    assert item.weight == weight  # type: ignore
    assert item.item_name == item_name
    assert item.amount == item.qty * item.rate  # type: ignore


def test_purchase_return_split_combinations_in_voucher(purchase_return: PurchaseReturn):
    items: list[AnyChildItem] = list(  # type: ignore
        merge_same_items(purchase_return._voucher.get_items_to_sell(True))
    )
    purchase_return._add_missing_field_to_voucher_items_to_sell(items)
    purchase_return._split_combinations_in_voucher()

    def build_shorten_item(item: AnyChildItem) -> dict[str, str | int | None]:
        return {
            "item_code": item.item_code,
            "item_name": item.item_name,
            "qty": item.qty,
            "rate": item.rate,  # type: ignore
            "amount": item.qty * item.rate,  # type: ignore
        }

    assert [build_shorten_item(i) for i in items] == [
        build_shorten_item(i) for i in purchase_return._voucher.items_to_sell
    ]


def test_purchase_return_modify_voucher(purchase_return: PurchaseReturn):
    prev_qty_counter = count_qty(purchase_return._voucher.get_items_to_sell(True))
    purchase_return._modify_voucher()
    new_qty_counter = count_qty(purchase_return._voucher.get_items_to_sell(True))

    diff = prev_qty_counter.copy()
    for item_code in prev_qty_counter:
        diff[item_code] -= new_qty_counter[item_code]
        if diff[item_code] == 0:
            del diff[item_code]

    assert diff == count_qty(purchase_return.items)


@pytest.mark.parametrize("status", ("Draft", "Cancelled", "Random Status"))
def test_purchase_return_make_gl_entries_status_raises(
    purchase_return: PurchaseReturn, status: str
):
    purchase_return._voucher.status = status  # type: ignore
    with pytest.raises(KeyError):
        purchase_return._make_gl_entries()


@pytest.mark.parametrize(
    ("status", "exp_inventory_account"),
    (("To Receive", "prepaid_inventory"), ("Completed", "inventory")),
)
def test_purchase_return_make_gl_entries_create(
    purchase_return: PurchaseReturn,
    status: Literal["To Receive", "Completed"],
    exp_inventory_account: str,
):
    purchase_return._voucher.status = status
    purchase_return.returned_paid_amount = 1000
    purchase_return._make_gl_entries()

    entries = get_all(
        GLEntry,
        fields=("account", "debit", "credit"),
        filters={
            "voucher_type": purchase_return.doctype,
            "voucher_no": purchase_return.name,
        },
    )
    assert len(entries) == 2

    bank_account = get_account("bank")
    inventory_account = get_account(exp_inventory_account)
    for entry in entries:
        assert entry.account in (bank_account, inventory_account)
        if entry.account == bank_account:
            assert entry.debit == 1000
            assert entry.credit == 0
        elif entry.account == inventory_account:
            assert entry.debit == 0
            assert entry.credit == 1000


@pytest.mark.parametrize("status", ("Draft", "Cancelled", "Random Status"))
def test_purchase_return_make_stock_entries_not_create(
    purchase_return: PurchaseReturn, status: str
):
    purchase_return._voucher.status = status  # type: ignore
    with pytest.raises(KeyError):
        purchase_return._make_stock_entries()


@pytest.mark.parametrize(
    ("status", "exp_stock_type"),
    (("To Receive", "Available Purchased"), ("Completed", "Available Actual")),
)
def test_purchase_return_make_stock_entries_create(
    purchase_return: PurchaseReturn,
    status: Literal["To Receive", "Completed"],
    exp_stock_type: str,
):
    purchase_return._voucher.status = status
    purchase_return.db_insert()
    purchase_return._make_stock_entries()

    entry_name: str = get_value(
        "Stock Entry",
        {"voucher_type": purchase_return.doctype, "voucher_no": purchase_return.name},
    )
    counter = count_qty(purchase_return.items)
    for item_code in counter:
        counter[item_code] = -counter[item_code]
    doc = get_doc(StockEntry, entry_name)
    assert count_qty(doc.items) == counter
    assert doc.stock_type == exp_stock_type


def test_purchase_return_before_submit_items_to_sell_added_from_sales_return_are_deleted(
    purchase_return: PurchaseReturn,
):
    purchase_return._voucher.items_to_sell = []
    purchase_return._voucher.submit()
    purchase_return.items = []
    purchase_return.append(
        "items",
        {
            "item_code": "10014030",
            "qty": 2,
            "rate": 1000,
        },
    )
    purchase_return.save()
    purchase_return.before_submit()
    assert purchase_return._voucher.items_to_sell == []


def test_purchase_return_on_cancel_raises_on_invalid_status(
    purchase_return: PurchaseReturn,
):
    purchase_return._voucher.status = "Completed"
    with pytest.raises(
        frappe.ValidationError,
        match="Allowed to cancel Purchase Return only if status of Order is To Receive",
    ):
        purchase_return.on_cancel()


def test_purchase_return_on_cancel_not_raises_on_valid_status(
    purchase_return: PurchaseReturn,
):
    purchase_return._voucher.status = "To Receive"
    purchase_return.on_cancel()


def test_purchase_return_on_cancel_linked_docs_cancelled(
    purchase_return: PurchaseReturn, sales_order: SalesOrder
):
    purchase_return.db_insert()

    sales_order.db_set("docstatus", 1)
    sales_order.db_set("delivery_status", "Purchased")
    sales_order.reload()
    orders_to_items = purchase_return._allocate_items()
    purchase_return._make_sales_returns(orders_to_items)
    purchase_return._voucher.reload()
    purchase_return._voucher.status = "To Receive"
    purchase_return._voucher.db_update()
    purchase_return.before_submit()
    purchase_return.on_cancel()

    for doctype in (SalesReturn, GLEntry, StockEntry):
        docs = get_all(doctype, "docstatus")
        assert all(doc.docstatus == 2 for doc in docs)
