from __future__ import annotations

from types import SimpleNamespace

import pytest

from comfort.entities import Item
from comfort.finance import GLEntry
from comfort.finance.utils import get_account
from comfort.stock import Receipt, StockEntry
from comfort.transactions import PurchaseOrder, SalesOrder
from comfort.utils import get_all, get_doc, get_value, new_doc


def test_voucher_property(receipt_sales: Receipt):
    assert (
        receipt_sales._voucher.as_dict()
        == get_doc(SalesOrder, receipt_sales.voucher_no).as_dict()
    )


def test_new_gl_entry(receipt_sales: Receipt):
    account, debit, credit = "cash", 300, 0
    receipt_sales.db_insert()
    receipt_sales._new_gl_entry(account, debit, credit)

    values: tuple[str, int, int] = get_value(
        "GL Entry",
        filters={
            "voucher_type": receipt_sales.doctype,
            "voucher_no": receipt_sales.name,
        },
        fieldname=("account", "debit", "credit"),
    )

    assert get_account(account) == values[0]
    assert debit == values[1]
    assert credit == values[2]


@pytest.mark.parametrize("reverse_qty", (True, False, None))
def test_new_stock_entry(
    receipt_sales: Receipt, item_no_children: Item, reverse_qty: bool
):
    stock_type, items = "Reserved Actual", [
        SimpleNamespace(item_code=item_no_children.item_code, qty=5)
    ]
    receipt_sales.db_insert()
    receipt_sales._new_stock_entry(stock_type, items, reverse_qty=reverse_qty)

    entry_name: str = get_value(
        "Stock Entry",
        filters={
            "voucher_type": receipt_sales.doctype,
            "voucher_no": receipt_sales.name,
        },
    )
    entry = get_doc(StockEntry, entry_name)

    assert entry.items[0].item_code == items[0].item_code
    assert entry.items[0].qty == -items[0].qty if reverse_qty else items[0].qty


def test_receipt_create_sales_gl_entries(
    receipt_sales: Receipt, sales_order: SalesOrder
):
    sales_order.discount = 100
    sales_order.validate()
    sales_order.db_update()

    receipt_sales.create_sales_gl_entries()

    exp_entries = [
        {
            "account": get_account("inventory"),
            "debit": 0,
            "credit": sales_order.items_cost,
        },
        {
            "account": get_account("sales"),
            "debit": 0,
            "credit": sales_order.margin - sales_order.discount,
        },
        {
            "account": get_account("delivery"),
            "debit": 0,
            "credit": 400,
        },
        {
            "account": get_account("installation"),
            "debit": 0,
            "credit": 500,
        },
        {
            "account": get_account("prepaid_sales"),
            "debit": sales_order.total_amount,
            "credit": 0,
        },
    ]
    entries = get_all(
        GLEntry,
        field=("account", "debit", "credit"),
        filter={
            "voucher_type": receipt_sales.doctype,
            "voucher_no": receipt_sales.name,
        },
    )
    for entry in entries:
        assert dict(entry) in exp_entries  # type: ignore


def test_create_sales_stock_entries(receipt_sales: Receipt, sales_order: SalesOrder):
    sales_order.set_child_items()
    sales_order.db_update_all()
    receipt_sales.db_insert()
    receipt_sales.create_sales_stock_entries()

    entry_name: str = get_value(
        "Stock Entry",
        filters={
            "voucher_type": receipt_sales.doctype,
            "voucher_no": receipt_sales.name,
        },
    )
    entry = get_doc(StockEntry, entry_name)

    assert entry.stock_type == "Reserved Actual"
    for i in entry.items:
        assert i.qty < 0


def test_create_purchase_gl_entries(
    receipt_purchase: Receipt, purchase_order: PurchaseOrder
):
    purchase_order.items_to_sell_cost = 1530
    purchase_order.sales_orders_cost = 20000
    purchase_order.db_update()
    items_cost = purchase_order.items_to_sell_cost + purchase_order.sales_orders_cost

    receipt_purchase.db_insert()
    receipt_purchase.create_purchase_gl_entries()

    exp_entries = [
        {
            "account": get_account("prepaid_inventory"),
            "debit": 0,
            "credit": items_cost,
        },
        {
            "account": get_account("inventory"),
            "debit": items_cost,
            "credit": 0,
        },
    ]

    entries = get_all(
        GLEntry,
        field=("account", "debit", "credit"),
        filter={
            "voucher_type": receipt_purchase.doctype,
            "voucher_no": receipt_purchase.name,
        },
    )
    for entry in entries:
        assert dict(entry) in exp_entries  # type: ignore


def test_create_purchase_stock_entries_for_sales_orders(receipt_purchase: Receipt):
    receipt_purchase.db_insert()
    receipt_purchase._create_purchase_stock_entries_for_sales_orders()

    entries = get_all(
        StockEntry,
        filter={
            "voucher_type": receipt_purchase.doctype,
            "voucher_no": receipt_purchase.name,
        },
    )
    for entry in entries:
        entry = get_doc(StockEntry, entry.name)
        assert entry.stock_type in ("Reserved Purchased", "Reserved Actual")
        if entry.stock_type == "Reserved Purchased":
            for i in entry.items:
                assert i.qty < 0
        elif entry.stock_type == "Reserved Actual":
            for i in entry.items:
                assert i.qty > 0


def test_create_purchase_stock_entries_for_sales_orders_not_executed_if_no_items():
    purchase_order = new_doc(PurchaseOrder)
    purchase_order.db_insert()

    receipt_purchase = get_doc(
        Receipt,
        {"voucher_type": purchase_order.doctype, "voucher_no": purchase_order.name},
    )
    receipt_purchase.db_insert()
    receipt_purchase._create_purchase_stock_entries_for_sales_orders()

    first_entry_name: str | None = get_value(
        "Stock Entry",
        {"voucher_type": receipt_purchase.doctype, "voucher_no": receipt_purchase.name},
    )
    assert first_entry_name is None


def test_create_purchase_stock_entries_for_items_to_sell_executed(
    receipt_purchase: Receipt,
):
    receipt_purchase.db_insert()
    receipt_purchase._create_purchase_stock_entries_for_items_to_sell()

    entries = get_all(
        StockEntry,
        filter={
            "voucher_type": receipt_purchase.doctype,
            "voucher_no": receipt_purchase.name,
        },
    )
    for e in entries:
        entry = get_doc(StockEntry, e.name)
        assert entry.stock_type in ("Available Purchased", "Available Actual")
        if entry.stock_type == "Available Purchased":
            for i in entry.items:
                assert i.qty < 0
        elif entry.stock_type == "Available Actual":
            for i in entry.items:
                assert i.qty > 0


def test_create_purchase_stock_entries_for_items_to_sell_not_executed_if_no_item(
    receipt_purchase: Receipt, purchase_order: PurchaseOrder
):
    for doc in purchase_order.items_to_sell:
        doc.delete()
    purchase_order.items_to_sell = []
    purchase_order.db_update_all()

    receipt_purchase.db_insert()
    receipt_purchase._create_purchase_stock_entries_for_items_to_sell()

    first_entry_name: str | None = get_value(
        "Stock Entry",
        {"voucher_type": receipt_purchase.doctype, "voucher_no": receipt_purchase.name},
    )
    assert first_entry_name is None


@pytest.mark.parametrize("docstatus", (0, 1))
def test_set_status_in_voucher_sales_order(sales_order: SalesOrder, docstatus: int):
    sales_order.docstatus = docstatus
    sales_order.delivery_status = "To Deliver"
    sales_order.update_items_from_db()
    sales_order.calculate()
    sales_order.db_insert()
    sales_order.db_update_all()
    sales_order.add_receipt()

    receipt_name: str = get_value(
        "Receipt", {"voucher_type": sales_order.doctype, "voucher_no": sales_order.name}
    )
    receipt = get_doc(Receipt, receipt_name)
    receipt.docstatus = 2
    receipt.db_update()
    receipt.set_status_in_voucher()

    sales_order.reload()
    assert sales_order.delivery_status != "Delivered"


def test_set_status_in_voucher_purchase_order(receipt_purchase: Receipt):
    receipt_purchase._voucher.status = "Completed"
    receipt_purchase._voucher.db_update()
    receipt_purchase.set_status_in_voucher()
    receipt_purchase._voucher.reload()
    assert receipt_purchase._voucher.status == "To Receive"
