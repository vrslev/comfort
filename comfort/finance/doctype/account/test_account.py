import unittest

import frappe
from frappe.model.document import Document


class TestAccount(unittest.TestCase):
    def test_account_created(self):
        self.assertTrue(
            create_account("_Test Company", "SBI - _C", "Asset", "Bank Accounts - _C")
        )


def create_account(
    company: str, account_name: str, root_type: str, parent_account: str
):
    account: Document = frappe.db.get_value(
        "Account", filters={"account_name": account_name, "company": company}
    )
    if account:
        return account
    else:
        account = frappe.new_doc("Account")
        account.account_name = account_name
        account.root_type = root_type
        account.parent_account = parent_account
        account.company = company
        account.insert()
        return account