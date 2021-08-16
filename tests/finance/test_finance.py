import re
from typing import TYPE_CHECKING

import pytest

from comfort.finance import get_account, get_received_amount
from comfort.finance.chart_of_accounts import DEFAULT_ACCOUNT_SETTINGS
from comfort.finance.doctype.gl_entry.gl_entry import GLEntry
from comfort.transactions.doctype.sales_order.sales_order import SalesOrder

if not TYPE_CHECKING:
    from tests.finance.test_chart_of_accounts import accounts
    from tests.finance.test_gl_entry import gl_entry
    from tests.transactions.test_sales_order import sales_order


def test_get_account(accounts: None):
    default_accounts = (list(t) for t in DEFAULT_ACCOUNT_SETTINGS.items())

    for l in default_accounts:
        l[0] = re.findall(r"default_(.*)_account", l[0])[0]
        assert get_account(l[0]) == l[1]  # from string
    assert get_account(l[0] for l in default_accounts) == [  # from list
        l[1] for l in default_accounts
    ]


def test_get_account_raises_on_wrong_name(accounts: None):
    account_name = "toys"
    with pytest.raises(
        ValueError, match=f'Account Settings has no field "{account_name}"'
    ):
        get_account(account_name)


def test_get_received_amount(
    accounts: None, gl_entry: GLEntry, sales_order: SalesOrder
):
    sales_order.db_insert()
    get_received_amount(sales_order)
