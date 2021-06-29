import unittest

import frappe
from comfort.comfort.doctype.company.test_company import create_company
from frappe.utils import flt, nowdate


class TestSalesOrder(unittest.TestCase):
    def setUp(self):
        create_company("_Test Company")

    def test_sales_order_creation(self):
        so = make_sales_order("Poco F2", 10, "Rohan", True, False)
        self.assertTrue(get_sales_order(so.name))
        items_quantity, items_amount = 0, 0
        for item in so.items:
            items_quantity += flt(item.qty)
            items_amount += flt(item.amount)
        self.assertEqual(so.total_quantity, items_quantity)
        self.assertEqual(so.total_amount, items_amount)

    def test_sales_order_validation(self):
        so = make_sales_order("Poco F2", -10, "Rohan", False, False)
        self.assertRaises(frappe.exceptions.ValidationError, so.insert)

        so = make_sales_order("Poco F2", 0, "Rohan", False, False)
        self.assertRaises(frappe.exceptions.ValidationError, so.insert)


def make_sales_order(item_name, qty, customer, save=True, submit=False):
    so = frappe.new_doc("Sales Order")
    so.customer = customer
    so.posting_date = nowdate()
    so.company = "_Test Company"
    so.set("items", [{"item": item_name, "qty": qty}])

    if save or submit:
        so.insert()
        if submit:
            so.submit()

    return so


def get_sales_order(name):
    return frappe.db.sql(
        """ SELECT
					*
				FROM
					`tabSales Order`
				WHERE
					name=%s """,
        name,
        as_dict=1,
    )
