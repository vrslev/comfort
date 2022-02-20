# type: ignore
customers = {"Customer name": "VK URL"}
sales_orders = [
    {
        "name": "Previous order name",
        "customer": "Customer name",
        "items": [{"item_code": "Item Code", "qty": "Qty"}],
    }
]
user = "ERP User"
site_name = "Site Name"

import frappe
from comfort import new_doc
from comfort.integrations._ikea import fetch_items
from comfort.integrations.browser_ext import _create_customer
from comfort.transactions.doctype.purchase_order.purchase_order import PurchaseOrder
from comfort.transactions.doctype.sales_order.sales_order import SalesOrder

frappe.init(site_name, sites_path="../../sites")
frappe.connect()
frappe.set_user(user)
purchase_order = new_doc(PurchaseOrder)
purchase_order.name = "Список ожидания"
unsuccessful = []


def add_order(customer_name, items, fetch_result):
    sales_order = new_doc(SalesOrder)
    sales_order.customer = customer_name
    sales_order.extend(
        "items",
        [item for item in items if item["item_code"] in fetch_result["successful"]],
    )
    sales_order.save()
    return sales_order


for so_info in sales_orders:
    customer = _create_customer(so_info["customer"], customers[so_info["customer"]])
    fetch_result = fetch_items(
        [i["item_code"] for i in so_info["items"]], force_update=True
    )
    if not fetch_result["successful"]:
        unsuccessful.append(so_info["name"])
        continue
    sales_order = add_order(customer.name, so_info["items"], fetch_result)
    purchase_order.append("sales_orders", {"sales_order_name": sales_order.name})

print(unsuccessful)
purchase_order.save()
frappe.db.commit()
