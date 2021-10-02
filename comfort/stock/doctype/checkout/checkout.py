from typing import Literal

import frappe
from comfort import TypedDocument, get_doc
from comfort.stock import cancel_stock_entries_for, create_stock_entry
from comfort.transactions.doctype.purchase_order.purchase_order import PurchaseOrder


class Checkout(TypedDocument):
    doctype: Literal["Checkout"]
    purchase_order: str

    def before_submit(self):
        doc = get_doc(PurchaseOrder, self.purchase_order)
        if doc.sales_orders:
            create_stock_entry(
                self.doctype,
                self.name,
                "Reserved Purchased",
                doc.get_items_in_sales_orders(True),
            )

        if doc.items_to_sell:
            create_stock_entry(
                self.doctype,
                self.name,
                "Available Purchased",
                doc.get_items_to_sell(True),
            )

    def set_purchase_draft_status(self):
        frappe.db.set_value("Purchase Order", self.purchase_order, "status", "Draft")

    def before_cancel(self):  # pragma: no cover
        cancel_stock_entries_for(self.doctype, self.name)
        self.set_purchase_draft_status()
