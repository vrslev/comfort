from __future__ import annotations

from collections import defaultdict
from typing import Any

import frappe
from comfort import group_by_key
from comfort.finance.doctype.account.account import Account
from frappe import _


def execute(filters: dict[str, str]):  # pragma: no cover
    data = get_data(filters)
    income, expenses, profit_loss = get_income_expenses_profit_loss_totals(data)
    return (
        get_columns(),
        data,
        None,
        get_chart_data(filters, income, expenses, profit_loss),
        get_report_summary(income, expenses, profit_loss),
    )


def get_columns():  # pragma: no cover
    return [
        {
            "fieldname": "name",
            "label": "Account",
            "fieldtype": "Link",
            "options": "Account",
            "width": 300,
        },
        {
            "fieldname": "total",
            "label": "Total",
            "fieldtype": "Currency",
            "width": 150,
        },
    ]


def _get_parent_children_accounts_map() -> dict[str | None, list[Account]]:
    accounts: list[Account] = frappe.get_all("Account", ("name", "parent_account"))
    acceptable_parents = (_("Income"), _("Expenses"))
    to_remove: list[Account] = []
    for account in accounts:
        if account.parent_account is None and account.name not in acceptable_parents:
            to_remove.append(account)
    for account in to_remove:
        accounts.remove(account)
    return group_by_key(accounts, key="parent_account")


def _filter_accounts(parent_children_map: dict[str | None, list[Account]]):
    filtered_accounts: list[Account] = []

    def add_to_list(parent: str | None, level: int):
        for child in parent_children_map.get(parent, []):
            child.indent = level
            filtered_accounts.append(child)
            # Try to run over children of this child
            add_to_list(child.name, level + 1)

    add_to_list(None, 0)
    return filtered_accounts


def _get_account_balance_map(filters: dict[str, str]):
    entries: list[Any] = frappe.get_all(
        "GL Entry",
        fields=("account", "(debit - credit) as balance"),
        filters=(
            ("docstatus", "!=", 2),
            ("creation", "between", (filters["from_date"], filters["to_date"])),
        ),
    )
    account_balance_map: defaultdict[str, int] = defaultdict(int)
    for entry in entries:
        account_balance_map[entry.account] += abs(entry.balance)
    return account_balance_map


def _calculate_total_in_parent_accounts(
    account_balance_map: defaultdict[str, int],
    parent_children_map: dict[str | None, list[Account]],
    accounts: list[Account],
):
    for account in reversed(accounts):
        account.total = account_balance_map[account.name]
        children: list[Account] = parent_children_map.get(account.name)
        if children:
            account_balance_map[account.name] = account.total = sum(
                account_balance_map[c.name] for c in children
            )


def get_data(filters: dict[str, str]):  # pragma: no cover
    account_balance_map = _get_account_balance_map(filters)
    parent_children_map = _get_parent_children_accounts_map()
    accounts = _filter_accounts(parent_children_map)
    _calculate_total_in_parent_accounts(
        account_balance_map, parent_children_map, accounts
    )
    return accounts


def get_income_expenses_profit_loss_totals(data: list[Account]):
    income: int = 0
    expenses: int = 0
    for account in data:
        if account.name == _("Income"):
            income = account.total
        elif account.name == _("Expenses"):
            expenses = account.total
    return income, expenses, income - expenses


def get_chart_data(
    filters: dict[str, str], income: int, expenses: int, profit_loss: int
):
    return {
        "data": {
            "labels": [f"{filters['from_date']}—{filters['to_date']}"],
            "datasets": [
                {"name": "Income", "values": [income]},
                {"name": "Expenses", "values": [expenses]},
                {"name": "Profit/Loss", "values": [profit_loss]},
            ],
        },
        "type": "bar",
    }


def get_report_summary(income: int, expenses: int, profit_loss: int):
    return [
        {"value": income, "label": "Income", "datatype": "Currency"},
        {"value": expenses, "label": "Expenses", "datatype": "Currency"},
        {
            "value": profit_loss,
            "indicator": "Green" if profit_loss >= 0 else "Red",
            "label": "Total Profit This Year",
            "datatype": "Currency",
        },
    ]
