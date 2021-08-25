import frappe
from comfort.transactions.doctype.purchase_order.purchase_order import PurchaseOrder
from comfort.transactions.doctype.sales_order.sales_order import SalesOrder
from comfort.transactions.doctype.sales_order.sales_order_list import (
    get_sales_orders_not_in_purchase_order,
)


def test_get_sales_orders_not_in_purchase_order(
    sales_order: SalesOrder, purchase_order: PurchaseOrder
):
    purchase_order.db_insert()
    purchase_order.db_update_all()
    new_name = "random_name"
    new_sales_order: SalesOrder = frappe.get_doc(
        {"doctype": "Sales Order", "name": new_name}
    )
    new_sales_order.db_insert()

    res = get_sales_orders_not_in_purchase_order()
    assert sales_order.name not in res
    assert new_sales_order.name in res
