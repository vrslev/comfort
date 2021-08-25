from __future__ import annotations

import frappe
from comfort import count_quantity
from comfort.stock import cancel_stock_entries_for, create_receipt, create_stock_entry
from comfort.stock.doctype.receipt.receipt import Receipt
from comfort.stock.doctype.stock_entry.stock_entry import StockEntry
from comfort.transactions.doctype.sales_order.sales_order import SalesOrder


def test_create_receipt(sales_order: SalesOrder):
    sales_order.db_insert()
    sales_order.db_update_all()
    create_receipt(sales_order.doctype, sales_order.name)
    docstatus: int = frappe.get_value(
        "Receipt",
        fieldname="docstatus",
        filters={"voucher_type": sales_order.doctype, "voucher_no": sales_order.name},
    )
    assert docstatus == 1


def test_create_stock_entry(sales_order: SalesOrder):
    sales_order.db_insert()
    sales_order.db_update_all()

    stock_type = "Reserved Actual"
    items_obj = sales_order._get_items_with_splitted_combinations()
    items = [
        {"item_code": item_code, "qty": qty}
        for item_code, qty in count_quantity(items_obj).items()
    ]
    create_stock_entry(sales_order.doctype, sales_order.name, stock_type, items)

    entry_name: str | None = frappe.get_value(
        "Stock Entry",
        filters={"voucher_type": sales_order.doctype, "voucher_no": sales_order.name},
    )
    assert entry_name is not None

    doc: StockEntry = frappe.get_doc("Stock Entry", entry_name)
    exp_items = count_quantity(items_obj).items()
    for i in count_quantity(doc.items).items():
        assert i in exp_items

    assert doc.docstatus == 1
    assert doc.stock_type == stock_type


def test_cancel_stock_entries_for(receipt_sales: Receipt):
    receipt_sales.insert()
    receipt_sales.submit()
    cancel_stock_entries_for(receipt_sales.doctype, receipt_sales.name)

    entries: list[StockEntry] = frappe.get_all(
        "Stock Entry",
        "docstatus",
        filters={
            "voucher_type": receipt_sales.doctype,
            "voucher_no": receipt_sales.name,
        },
    )
    for entry in entries:
        assert entry.docstatus == 2
