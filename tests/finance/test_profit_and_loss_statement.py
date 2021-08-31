import pytest

import frappe
from comfort import group_by_attr
from comfort.finance.doctype.account.account import Account
from comfort.finance.doctype.gl_entry.gl_entry import GLEntry
from comfort.finance.report.profit_and_loss_statement.profit_and_loss_statement import (
    _calculate_total_in_parent_accounts,
    _filter_accounts,
    _get_account_balance_map,
    _get_parent_children_accounts_map,
    get_chart_data,
    get_data,
    get_income_expense_profit_loss_totals,
    get_report_summary,
)
from frappe.utils import get_datetime_str, today
from tests.finance.test_general_ledger import insert_gl_entries_with_wrong_conditions


@pytest.mark.usefixtures("accounts")
def test_get_parent_children_accounts_map():
    accounts: list[Account] = frappe.get_all("Account", ("name", "parent_account"))
    to_remove: list[Account] = []
    for account in accounts:
        if account.parent_account is None and account.name not in (
            "Income",
            "Expense",
        ):
            to_remove.append(account)
    for account in to_remove:
        accounts.remove(account)

    assert _get_parent_children_accounts_map() == group_by_attr(
        accounts, "parent_account"
    )


@pytest.mark.usefixtures("accounts")
def test_filter_accounts():
    assert _filter_accounts(_get_parent_children_accounts_map()) == [
        {"name": "Income", "parent_account": None, "indent": 0},
        {"name": "Service", "parent_account": "Income", "indent": 1},
        {"name": "Installation", "parent_account": "Service", "indent": 2},
        {"name": "Delivery", "parent_account": "Service", "indent": 2},
        {"name": "Sales", "parent_account": "Income", "indent": 1},
        {"name": "Purchase Compensations", "parent_account": "Income", "indent": 1},
        {"name": "Expense", "parent_account": None, "indent": 0},
        {"name": "Sales Compensations", "parent_account": "Expense", "indent": 1},
        {"name": "Purchase Delivery", "parent_account": "Expense", "indent": 1},
        {"name": "Cost of Goods Sold", "parent_account": "Expense", "indent": 1},
    ]


def get_filters() -> dict[str, str]:
    return {
        "from_date": "2021-07-31",
        "to_date": get_datetime_str(today()),
    }


def test_get_account_balance_map(gl_entry: GLEntry):
    insert_gl_entries_with_wrong_conditions(gl_entry)
    assert dict(_get_account_balance_map(get_filters())) == {"Delivery": 300}


def test_calculate_total_in_parent_accounts(gl_entry: GLEntry):
    insert_gl_entries_with_wrong_conditions(gl_entry)
    gl_entry.account = "Installation"
    gl_entry.name = None
    gl_entry.credit = 250
    gl_entry.db_insert()

    account_balance_map = _get_account_balance_map(get_filters())
    parent_children_map = _get_parent_children_accounts_map()
    accounts = _filter_accounts(parent_children_map)
    _calculate_total_in_parent_accounts(
        account_balance_map, parent_children_map, accounts
    )

    for account in accounts:
        if account.name in ("Income", "Service"):
            assert account.total == 550
        elif account.name == "Delivery":
            assert account.total == 300
        elif account.name == "Installation":
            assert account.total == 250
        else:
            assert account.total == 0


def generate_income_expense_profit_loss_totals(gl_entry: GLEntry):
    insert_gl_entries_with_wrong_conditions(gl_entry)
    data = get_data(get_filters())
    return get_income_expense_profit_loss_totals(data)


def test_get_income_expense_profit_loss_totals(gl_entry: GLEntry):
    income, expense, profit_loss = generate_income_expense_profit_loss_totals(gl_entry)
    assert income == 300
    assert expense == 0
    assert profit_loss == 300


def test_get_chart_data():
    income, expense, profit_loss = 300, 200, 100
    filters = get_filters()
    chart = get_chart_data(filters, income, expense, profit_loss)
    assert chart["data"]["labels"][0] == f"{filters['from_date']}—{filters['to_date']}"
    for dataset in chart["data"]["datasets"]:
        if dataset["name"] == "Income":
            assert dataset["values"][0] == income
        elif dataset["name"] == "Expense":
            assert dataset["values"][0] == expense
        elif dataset["name"] == "Profit/Loss":
            assert dataset["values"][0] == profit_loss


@pytest.mark.parametrize(
    ("income", "expense", "profit_loss", "indicator"),
    (
        (300, 200, 100, "Green"),
        (300, 300, 0, "Green"),
        (200, 300, -100, "Red"),
    ),
)
def test_get_report_summary(
    income: int, expense: int, profit_loss: int, indicator: str
):
    for v in get_report_summary(income, expense, profit_loss):
        if v["label"] == "Income":
            assert v["value"] == income
        elif v["label"] == "Expense":
            assert v["value"] == expense
        elif v["label"] == "Total Profit This Year":
            assert v["value"] == profit_loss
            assert v["indicator"] == indicator