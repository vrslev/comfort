import frappe
from comfort.stock import cancel_stock_entries_for, create_stock_entry
from comfort.transactions.doctype.purchase_order.purchase_order import PurchaseOrder
from frappe.model.document import Document


class Checkout(Document):
    purchase_order: str

    def before_submit(self):
        doc: PurchaseOrder = frappe.get_doc("Purchase Order", self.purchase_order)
        if doc.sales_orders:
            create_stock_entry(
                self.doctype,
                self.name,
                "Reserved Purchased",
                doc._get_items_in_sales_orders(True),
            )

        if doc.items_to_sell:
            create_stock_entry(
                self.doctype,
                self.name,
                "Available Purchased",
                doc._get_items_to_sell(True),
            )

    def before_cancel(self):  # pragma: no cover
        cancel_stock_entries_for(self.doctype, self.name)
