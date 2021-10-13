from __future__ import annotations

from typing import Any

import pytest

from comfort import get_all
from comfort.finance.chart_of_accounts import ACCOUNTS
from comfort.finance.doctype.account.account import Account


def get_accounts_from_schema():
    accounts: list[dict[str, str | None]] = []

    def execute(parent: str | None, children: dict[str, Any]):
        for child, children_of_child in children.items():
            account = {"name": child, "parent_account": parent}
            accounts.append(account)
            execute(child, children_of_child)

    execute(None, ACCOUNTS)
    return accounts


@pytest.mark.usefixtures("accounts")
def test_create_accounts_from_schema():
    accounts_from_schema = get_accounts_from_schema()
    accounts: list[Account] = get_all(Account, ("name", "parent_account"))
    created_accounts: list[dict[str, str | None]] = [
        dict(a) for a in accounts  # type: ignore
    ]

    not_matching_accounts: list[dict[str, str | None]] = [
        acc
        for acc in accounts_from_schema + created_accounts
        if acc not in accounts_from_schema or acc not in created_accounts
    ]
    assert len(not_matching_accounts) == 0
