import frappe
from comfort.transactions.doctype.purchase_order_sales_order.purchase_order_sales_order import (
    PurchaseOrderSalesOrder,
)


@frappe.whitelist()
def get_sales_orders_not_in_purchase_order() -> list[str]:
    po_sales_orders: list[PurchaseOrderSalesOrder] = frappe.get_all(
        "Purchase Order Sales Order", "sales_order_name"
    )
    return [
        s.name
        for s in frappe.get_all(
            "Sales Order",
            {"name": ("not in", (s.sales_order_name for s in po_sales_orders))},
        )
    ]
