from typing import TYPE_CHECKING

import pytest

import frappe
from comfort.transactions.doctype.purchase_order.purchase_order import PurchaseOrder
from comfort.transactions.doctype.sales_order.sales_order import SalesOrder

if not TYPE_CHECKING:
    from tests.entities.test_customer import customer
    from tests.entities.test_item import child_items, item
    from tests.transactions.test_sales_order import sales_order


@pytest.fixture
def purchase_order(sales_order: SalesOrder) -> PurchaseOrder:
    sales_order.set_child_items()
    sales_order.db_insert()
    sales_order.db_update_all()

    return frappe.get_doc(
        {
            "name": "Август-1",
            "docstatus": 0,
            "status": "Draft",
            "doctype": "Purchase Order",
            "delivery_options": [],
            "sales_orders": [
                {
                    "sales_order_name": "SO-2021-0001",
                    "customer": "Pavel Durov",
                    "total": 24660,
                }
            ],
            "items_to_sell": [
                {
                    "item_code": "29128569",
                    "qty": 1,
                }
            ],
        }
    )
