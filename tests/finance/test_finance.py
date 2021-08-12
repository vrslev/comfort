import re

# import frappe
# from comfort.entities.doctype.customer.customer import Customer
from comfort.finance import (  # make_gl_entry,; make_reverse_gl_entry,; make_cancelled_gl_entry,; cancel_gl_entry,; get_paid_amount,
    get_account,
)
from comfort.finance.chart_of_accounts import DEFAULT_ACCOUNT_SETTINGS
from tests.finance.test_chart_of_accounts import (
    accounts,  # type: ignore (need to use accounts fixture)
)

# import pytest


# @pytest.fixture
# def document(customer: Customer):
#     frappe._dict({
#         "customer": customer.name,
#         "doctype": "Sales Order",
#         "name": ""# TODO: Need to write tests for Sales Order first (for fixtures)

#     })

# def test_make_gl_entry():
#     ...


def test_get_account(accounts: None):
    default_accounts = [list(t) for t in DEFAULT_ACCOUNT_SETTINGS.items()]
    for l in default_accounts:
        l[0] = re.findall(r"default_(.*)_account", l[0])[0]
        assert get_account(l[0]) == l[1]  # from string
    assert get_account([l[0] for l in default_accounts]) == [
        l[1] for l in default_accounts
    ]  # from list
