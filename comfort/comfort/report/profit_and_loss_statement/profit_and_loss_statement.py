import frappe


def execute(filters=None):
    columns, data = [], []

    period_key, period_label = "Date Range", "Date Range"
    date = [filters.from_date, filters.to_date]

    columns = get_columns(period_key, period_label)

    income = get_data(date, "Income", "Credit", period_key)
    expense = get_data(date, "Expense", "Debit", period_key)

    data = []
    data.extend(income or [])
    data.extend(expense or [])

    profit_loss, income, expense = get_profit_loss_amount(data, period_key)
    data.append({"account": "Profit for the year", period_key: profit_loss})

    chart = get_chart_data(
        filters, columns, income, expense, data[-1][period_key], period_key
    )
    report_summary = get_report_summary(data, period_key)

    return columns, data, None, chart, report_summary


def get_columns(period_key, period_label):
    columns = [
        {
            "fieldname": "account",
            "label": "Account",
            "fieldtype": "Link",
            "options": "Account",
            "width": 300,
        },
        {
            "fieldname": period_key,
            "label": period_label,
            "fieldtype": "Currency",
            "options": "currency",
            "width": 150,
        },
    ]
    return columns


def get_data(date, root_type, dr_cr, period_key):
    accounts = get_accounts(root_type)
    data = []
    if accounts:
        i = 0
        for d in accounts:
            if d.parent_account == None or d.parent_account == data[-1]["account"]:
                append(data, d, i, period_key)
                i += 1
            else:
                for a in data:
                    if a["account"] == d.parent_account:
                        i = a["indent"] + 1
                        break
                append(data, d, i, period_key)
                i += 1
    temp = []
    for d in data:
        bal = get_account_balance(d["account"], date)
        if bal:
            d[period_key] = abs(bal)
            temp.append(d)
    for t in temp:
        for d in data:
            if d["account"] == t["parent_account"]:
                if d[period_key] == 0:
                    d[period_key] = t[period_key]
                    temp.append(d)
                else:
                    d[period_key] += t[period_key]
    data = [d for d in data if d[period_key] != 0]
    if data:
        data.append(
            {
                "account": "Total " + root_type + " (" + dr_cr + ")",
                period_key: data[0][period_key],
            }
        )
        data.append({})
    return data


def append(data, d, i, period_key):
    data.append(
        {
            "account": d.name,
            "account_type": d.account_type,
            "parent_account": d.parent_account,
            "indent": i,
            "has_value": d.is_group,
            period_key: 0,
        }
    )


def get_accounts(root_type):
    return frappe.db.sql(
        """ SELECT 
				name, parent_account, lft, root_type, account_type, is_group
			FROM 
				tabAccount
			WHERE 
				root_type=%s 
			ORDER BY 
				lft""",
        (root_type),
        as_dict=1,
    )


def get_account_balance(account, date):
    return frappe.db.sql(
        """ SELECT 
					sum(debit_amount) - sum(credit_amount) 
				FROM 
					`tabGL Entry` 
				WHERE 
					is_cancelled=0 and account=%s and posting_date>=%s and posting_date<=%s""",
        (account, date[0], date[1]),
    )[0][0]


def get_profit_loss_amount(data, period_key):
    income, expense = 0, 0
    for d in data:
        if d and d["account"] == "Total Income (Credit)":
            income = d[period_key]
        elif d and d["account"] == "Total Expense (Debit)":
            expense = d[period_key]
    profit_loss = income - expense
    return profit_loss, income, expense


def get_report_summary(data, period_key):
    profit, income, expense = get_profit_loss_amount(data, period_key)

    report_summary = [
        {"value": income, "label": "Income", "datatype": "Currency", "currency": "₹"},
        {"value": expense, "label": "Expense", "datatype": "Currency", "currency": "₹"},
        {
            "value": profit,
            "indicator": "Green" if profit > 0 else "Red",
            "label": "Total Profit This Year",
            "datatype": "Currency",
            "currency": "₹",
        },
    ]
    return report_summary


def get_chart_data(filters, columns, income, expense, profit, period_key):
    labels = [period_key]

    income_data, expense_data, profit_data = [], [], []

    if income != 0:
        income_data.append(income)
    if expense != 0:
        expense_data.append(expense)
    if profit != 0:
        profit_data.append(profit)

    datasets = []
    if income_data:
        datasets.append({"name": "Income", "values": income_data})
    if expense_data:
        datasets.append({"name": "Expense", "values": expense_data})
    if profit_data:
        datasets.append({"name": "Net Profit/Loss", "values": profit_data})

    chart = {"data": {"labels": labels, "datasets": datasets}}

    chart["type"] = "bar"

    return chart
