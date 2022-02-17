from comfort import count_qty, get_all, get_doc
from comfort.stock.doctype.checkout.checkout import Checkout
from comfort.stock.doctype.stock_entry.stock_entry import StockEntry
from comfort.transactions.doctype.purchase_order.purchase_order import PurchaseOrder


def test_checkout_before_submit(checkout: Checkout, purchase_order: PurchaseOrder):
    checkout.before_submit()

    entry_names = get_all(
        StockEntry,
        filter={
            "voucher_type": purchase_order.doctype,
            "voucher_no": purchase_order.name,
        },
    )

    for name in entry_names:
        doc = get_doc(StockEntry, name)
        assert doc.stock_type in ("Reserved Purchased", "Available Purchased")
        if doc.stock_type == "Reserved Purchased":
            exp_items = count_qty(purchase_order.get_items_in_sales_orders(True))
            for i in count_qty(doc.items):
                assert i in exp_items

        elif doc.stock_type == "Available Purchased":
            exp_items = count_qty(purchase_order.get_items_to_sell(True))
            for i in count_qty(doc.items):
                assert i in exp_items


def test_set_purchase_draft_status(checkout: Checkout, purchase_order: PurchaseOrder):
    checkout.db_insert()
    purchase_order.reload()
    purchase_order.status = "To Receive"
    checkout.set_purchase_draft_status()
    purchase_order.reload()
    assert purchase_order.status == "Draft"
