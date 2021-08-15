import frappe


@frappe.whitelist()
def get_sales_orders_in_purchase_order() -> list[str]:
    return [
        d.sales_order_name
        for d in frappe.get_all("Purchase Order Sales Order", "sales_order_name")
    ]
