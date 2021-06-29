import unittest

import frappe


class TestCompany(unittest.TestCase):
    def test_company_created(self):
        self.assertTrue(create_company("_Test Company Again"))


def create_company(company_name):
    abbr = "".join(c[0].upper() for c in company_name.split())
    company = frappe.db.get_value("Company", filters={"company_name": company_name})
    if company:
        return company
    else:
        company = frappe.new_doc("Company")
        company.company_name = company_name
        company.abbr = abbr
        company.insert()
        return company
