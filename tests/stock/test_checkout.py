import frappe
from comfort import count_quantity
from comfort.stock.doctype.checkout.checkout import Checkout
from comfort.stock.doctype.stock_entry.stock_entry import StockEntry
from comfort.transactions.doctype.purchase_order.purchase_order import PurchaseOrder


def test_checkout_before_submit(checkout: Checkout, purchase_order: PurchaseOrder):
    checkout.before_submit()

    entry_names: list[StockEntry] = frappe.get_all(
        "Stock Entry",
        filters={
            "voucher_type": purchase_order.doctype,
            "voucher_no": purchase_order.name,
        },
    )

    for name in entry_names:
        doc: StockEntry = frappe.get_doc("Stock Entry", name)
        assert doc.stock_type in ("Reserved Purchased", "Available Purchased")
        if doc.stock_type == "Reserved Purchased":
            exp_items = count_quantity(purchase_order._get_items_in_sales_orders(True))
            for i in count_quantity(doc.items):
                assert i in exp_items

        elif doc.stock_type == "Available Purchased":
            exp_items = count_quantity(purchase_order._get_items_to_sell(True))
            for i in count_quantity(doc.items):
                assert i in exp_items
