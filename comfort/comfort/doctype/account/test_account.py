import unittest

import frappe


class TestAccount(unittest.TestCase):
    def test_account_created(self):
        self.assertTrue(
            create_account(
                "_Test Company", "SBI - _C", "Asset", "Bank", "Bank Accounts - _C"
            )
        )


def create_account(company, account_name, root_type, account_type, parent_account):
    account = frappe.db.get_value(
        "Account", filters={"account_name": account_name, "company": company}
    )
    if account:
        return account
    else:
        account = frappe.new_doc("Account")
        account.account_name = account_name
        account.root_type = root_type
        account.account_type = account_type
        account.parent_account = parent_account
        account.company = company
        account.insert()
        return account
