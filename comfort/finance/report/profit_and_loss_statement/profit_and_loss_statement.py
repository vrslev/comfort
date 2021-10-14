from __future__ import annotations

from collections import defaultdict
from typing import Any

import frappe
from comfort import _, get_all, group_by_attr
from comfort.finance.doctype.account.account import Account

columns = [
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


def _get_parent_children_accounts_map() -> dict[str | None, list[AccountWithTotal]]:
    accounts: list[AccountWithTotal] = get_all(Account, ("name", "parent_account"))  # type: ignore
    acceptable_parents = ("Income", "Expense")
    to_remove: list[AccountWithTotal] = []
    for account in accounts:
        if account.parent_account is None and account.name not in acceptable_parents:
            to_remove.append(account)
    for account in to_remove:
        accounts.remove(account)
    return group_by_attr(accounts, "parent_account")


def _filter_accounts(parent_children_map: dict[str | None, list[AccountWithTotal]]):
    filtered_accounts: list[AccountWithTotal] = []

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
    account_balance_map: defaultdict[str | None, int] = defaultdict(int)
    for entry in entries:
        account_balance_map[entry.account] += abs(entry.balance)
    return account_balance_map


class AccountWithTotal(Account):
    total: int


def _calculate_total_in_parent_accounts(
    account_balance_map: defaultdict[str | None, int],
    parent_children_map: dict[str | None, list[AccountWithTotal]],
    accounts: list[AccountWithTotal],
):
    for account in reversed(accounts):
        account.total = account_balance_map[account.name]
        children: list[AccountWithTotal] | None = parent_children_map.get(account.name)
        if children is not None:
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


def get_income_expense_profit_loss_totals(data: list[AccountWithTotal]):
    income: int = 0
    expense: int = 0
    for account in data:
        if account.name == "Income":
            income = account.total
        elif account.name == "Expense":
            expense = account.total
    return income, expense, income - expense


def get_chart_data(
    filters: dict[str, str], income: int, expense: int, profit_loss: int
):
    return {
        "data": {
            "labels": [f"{filters['from_date']}—{filters['to_date']}"],
            "datasets": [
                {"name": _("Income"), "values": [income]},
                {"name": _("Expense"), "values": [expense]},
                {"name": _("Profit/Loss"), "values": [profit_loss]},
            ],
        },
        "type": "bar",
    }


def get_report_summary(income: int, expense: int, profit_loss: int):
    return [
        {"value": income, "label": _("Income"), "datatype": "Currency"},
        {"value": expense, "label": _("Expense"), "datatype": "Currency"},
        {
            "value": profit_loss,
            "indicator": "Green" if profit_loss >= 0 else "Red",
            "label": _("Total Profit This Year"),
            "datatype": "Currency",
        },
    ]


def execute(filters: dict[str, str]):  # pragma: no cover
    data = get_data(filters)
    income, expense, profit_loss = get_income_expense_profit_loss_totals(data)
    return (
        columns,
        data,
        None,
        get_chart_data(filters, income, expense, profit_loss),
        get_report_summary(income, expense, profit_loss),
    )
