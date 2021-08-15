import re
from typing import TYPE_CHECKING

from comfort.finance import get_account
from comfort.finance.chart_of_accounts import DEFAULT_ACCOUNT_SETTINGS

if not TYPE_CHECKING:
    from tests.finance.test_chart_of_accounts import accounts


# def test_make_gl_entry(): # TODO: Need to write tests for Sales Order first (for fixtures)


def test_get_account(accounts: None):
    default_accounts = [list(t) for t in DEFAULT_ACCOUNT_SETTINGS.items()]
    for l in default_accounts:
        l[0] = re.findall(r"default_(.*)_account", l[0])[0]
        assert get_account(l[0]) == l[1]  # from string
    assert get_account([l[0] for l in default_accounts]) == [
        l[1] for l in default_accounts
    ]  # from list
