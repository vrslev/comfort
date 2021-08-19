from __future__ import annotations

import frappe
from comfort.entities.doctype.item.item import Item
from comfort.finance import get_account
from comfort.stock.doctype.receipt.receipt import Receipt
from comfort.stock.doctype.stock_entry.stock_entry import StockEntry
from comfort.transactions.doctype.purchase_order.purchase_order import PurchaseOrder
from comfort.transactions.doctype.sales_order.sales_order import SalesOrder


def test_voucher_property(receipt_sales: Receipt):
    assert (
        receipt_sales._voucher.as_dict()
        == frappe.get_doc(
            receipt_sales.voucher_type, receipt_sales.voucher_no
        ).as_dict()
    )


def test_new_gl_entry(receipt_sales: Receipt):
    account, debit, credit = "cash", 300, 0
    receipt_sales.db_insert()
    receipt_sales._new_gl_entry(account, debit, credit)

    values: tuple[str, int, int] = frappe.get_value(
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


def test_new_stock_entry(receipt_sales: Receipt, item_no_children: Item):
    stock_type, items = "Reserved Actual", [
        {"item_code": item_no_children.item_code, "qty": 5}
    ]
    receipt_sales.db_insert()
    receipt_sales._new_stock_entry(stock_type, items)

    entry_name = frappe.get_value(
        "Stock Entry",
        filters={
            "voucher_type": receipt_sales.doctype,
            "voucher_no": receipt_sales.name,
        },
        fieldname="name",
    )
    entry: StockEntry = frappe.get_doc("Stock Entry", entry_name)

    assert entry.items[0].item_code == items[0]["item_code"]
    assert entry.items[0].qty == items[0]["qty"]


def test_create_sales_gl_entries(receipt_sales: Receipt, sales_order: SalesOrder):
    sales_order.items_cost = 500
    sales_order.db_update()

    receipt_sales.create_sales_gl_entries()

    exp_entries = [
        {
            "account": get_account("inventory"),
            "debit": 0,
            "credit": sales_order.items_cost,
        },
        {
            "account": get_account("cost_of_goods_sold"),
            "debit": sales_order.items_cost,
            "credit": 0,
        },
    ]
    entries: list[dict[str, str | int]] = frappe.get_all(
        "GL Entry",
        filters={
            "voucher_type": receipt_sales.doctype,
            "voucher_no": receipt_sales.name,
        },
        fields=("account", "debit", "credit"),
    )
    for entry in entries:
        assert dict(entry) in exp_entries


def test_create_sales_stock_entries(receipt_sales: Receipt, sales_order: SalesOrder):
    sales_order.set_child_items()
    sales_order.db_update_all()
    receipt_sales.db_insert()
    receipt_sales.create_sales_stock_entries()

    entry_name: str = frappe.get_value(
        "Stock Entry",
        filters={
            "voucher_type": receipt_sales.doctype,
            "voucher_no": receipt_sales.name,
        },
    )
    entry: StockEntry = frappe.get_doc("Stock Entry", entry_name)

    assert entry.stock_type == "Reserved Actual"
    for i in entry.items:
        assert i.qty < 0


def test_create_purchase_gl_entries(
    receipt_purchase: Receipt, purchase_order: PurchaseOrder
):
    purchase_order.items_to_sell_cost = 1530
    purchase_order.sales_order_cost = 20000
    purchase_order.db_update()
    items_cost = purchase_order.items_to_sell_cost + purchase_order.sales_order_cost

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

    entries: list[dict[str, str | int]] = frappe.get_all(
        "GL Entry",
        filters={
            "voucher_type": receipt_purchase.doctype,
            "voucher_no": receipt_purchase.name,
        },
        fields=("account", "debit", "credit"),
    )
    for entry in entries:
        assert dict(entry) in exp_entries


def test_create_purchase_stock_entries_for_sales_orders(receipt_purchase: Receipt):
    receipt_purchase.db_insert()
    receipt_purchase._create_purchase_stock_entries_for_sales_orders()

    entry_names: list[str] = frappe.get_all(
        "Stock Entry",
        filters={
            "voucher_type": receipt_purchase.doctype,
            "voucher_no": receipt_purchase.name,
        },
    )
    for name in entry_names:
        entry: StockEntry = frappe.get_doc("Stock Entry", name)
        assert entry.stock_type in ("Reserved Purchased", "Reserved Actual")
        if entry.stock_type == "Reserved Purchased":
            for i in entry.items:
                assert i.qty < 0
        elif entry.stock_type == "Reserved Actual":
            for i in entry.items:
                assert i.qty > 0


def test_create_purchase_stock_entries_for_sales_orders_not_executed_if_no_items(
    receipt_purchase: Receipt, purchase_order: PurchaseOrder
):
    for doc in purchase_order.sales_orders:
        doc.delete()
    purchase_order.sales_orders = []
    purchase_order.db_update_all()

    receipt_purchase.db_insert()
    receipt_purchase._create_purchase_stock_entries_for_sales_orders()

    first_entry_name: str | None = frappe.get_value(
        "Stock Entry",
        {"voucher_type": receipt_purchase.doctype, "voucher_no": receipt_purchase.name},
    )
    assert first_entry_name is None


def test_create_purchase_stock_entries_for_items_to_sell(receipt_purchase: Receipt):
    receipt_purchase.db_insert()
    receipt_purchase._create_purchase_stock_entries_for_items_to_sell()

    entry_names: list[str] = frappe.get_all(
        "Stock Entry",
        filters={
            "voucher_type": receipt_purchase.doctype,
            "voucher_no": receipt_purchase.name,
        },
    )
    for name in entry_names:
        entry: StockEntry = frappe.get_doc("Stock Entry", name)
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

    first_entry_name: str | None = frappe.get_value(
        "Stock Entry",
        {"voucher_type": receipt_purchase.doctype, "voucher_no": receipt_purchase.name},
    )
    assert first_entry_name is None
