from __future__ import annotations

from typing import Any

import pytest

import frappe
from comfort.finance.chart_of_accounts import ACCOUNTS, initialize_accounts


@pytest.fixture
def accounts():
    frappe.db.sql("DELETE FROM tabAccount")
    initialize_accounts()


def get_accounts_from_schema():
    accounts: list[dict[str, str]] = []

    def execute(parent: str, children: dict[str, Any]):
        for child, children_of_child in children.items():
            account = {"name": child, "parent_account": parent}
            accounts.append(account)
            execute(child, children_of_child)

    execute(None, ACCOUNTS)
    return accounts


def test_create_accounts_from_schema(accounts: None):
    accounts_from_schema = get_accounts_from_schema()
    created_accounts: list[dict[str, str | None]] = [
        dict(a) for a in frappe.get_all("Account", ["name", "parent_account"])
    ]

    not_matching_accounts: list[dict[str, str | None]] = [
        i
        for i in accounts_from_schema + created_accounts
        if i not in accounts_from_schema or i not in created_accounts
    ]
    assert len(not_matching_accounts) == 0
