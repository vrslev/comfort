import re

import pytest

from comfort.finance import get_account, get_received_amount
from comfort.finance.chart_of_accounts import DEFAULT_ACCOUNT_SETTINGS
from comfort.finance.doctype.payment.payment import Payment
from comfort.transactions.doctype.sales_order.sales_order import SalesOrder


def test_get_account(accounts: None):
    default_accounts = (list(t) for t in DEFAULT_ACCOUNT_SETTINGS.items())

    for acc in default_accounts:
        acc[0] = re.findall(r"default_(.*)_account", acc[0])[0]
        assert get_account(acc[0]) == acc[1]  # from string
    assert get_account(acc[0] for acc in default_accounts) == [  # from list
        acc[1] for acc in default_accounts
    ]


def test_get_account_raises_on_wrong_name(accounts: None):
    account_name = "toys"
    with pytest.raises(
        ValueError,
        match=f'Account Settings has no field "default_{account_name}_account"',
    ):
        get_account(account_name)


def test_get_received_amount(accounts: None, sales_order: SalesOrder):
    sales_order.db_insert()
    Payment.create_for(sales_order.doctype, sales_order.name, 300, True)
    assert get_received_amount(sales_order) == 300
