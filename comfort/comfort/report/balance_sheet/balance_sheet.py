import frappe


def execute(filters=None):
    columns, data = [], []

    period_key, period_label = "Date Range", "Date Range"
    date = [filters.from_date, filters.to_date]

    columns = get_columns(period_key, period_label)

    asset = get_data(date, "Asset", "Debit", period_key)
    liability = get_data(date, "Liability", "Credit", period_key)
    equity = get_data(date, "Equity", "Credit", period_key)

    data = []
    data.extend(asset or [])
    data.extend(liability or [])
    data.extend(equity or [])

    profit_loss, total, asset, liability, equity = get_profit_loss_total_amount(
        data, period_key
    )
    data.append(
        {"account": "Provisional Profit/Loss (Credit)", period_key: profit_loss}
    )
    data.append({"account": "Total (Credit)", period_key: total})

    chart = get_chart_data(filters, columns, asset, liability, equity, period_key)
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
            "parent_account": d.parent_account,
            "indent": i,
            "has_value": d.is_group,
            period_key: 0,
        }
    )


def get_accounts(root_type):
    return frappe.db.sql(
        """ SELECT
				name, parent_account, lft, root_type, is_group
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


def get_profit_loss_total_amount(data, period_key):
    debit, credit, l_credit, e_credit = 0, 0, 0, 0
    for d in data:
        if d and d["account"] == "Total Asset (Debit)":
            debit = d[period_key]
        elif d and d["account"] == "Total Liability (Credit)":
            l_credit = d[period_key]
            credit = d[period_key]
        elif d and d["account"] == "Total Equity (Credit)":
            e_credit = d[period_key]
            credit += d[period_key]
    profit_loss = debit - credit
    total = profit_loss + credit
    return profit_loss, total, debit, l_credit, e_credit


def get_report_summary(data, period_key):
    profit, total, asset, liability, equity = get_profit_loss_total_amount(
        data, period_key
    )

    report_summary = [
        {
            "value": asset,
            "indicator": "Green",
            "label": "Total Asset",
            "datatype": "Currency",
            "currency": "₹",
        },
        {
            "value": liability,
            "indicator": "Red",
            "label": "Total Liability",
            "datatype": "Currency",
            "currency": "₹",
        },
        {
            "value": equity,
            "indicator": "Blue",
            "label": "Total Equity",
            "datatype": "Currency",
            "currency": "₹",
        },
        {
            "value": profit,
            "indicator": "Green" if profit > 0 else "Red",
            "label": "Provisional Profit / Loss (Credit)",
            "datatype": "Currency",
            "currency": "₹",
        },
    ]
    return report_summary


def get_chart_data(filters, columns, asset, liability, equity, period_key):
    labels = [period_key]

    asset_data, liability_data, equity_data = [], [], []

    if asset != 0:
        asset_data.append(asset)
    if liability != 0:
        liability_data.append(liability)
    if equity != 0:
        equity_data.append(equity)

    datasets = []
    if asset_data:
        datasets.append({"name": "Assets", "values": asset_data})
    if liability_data:
        datasets.append({"name": "Liabilities", "values": liability_data})
    if equity_data:
        datasets.append({"name": "Equity", "values": equity_data})

    chart = {"data": {"labels": labels, "datasets": datasets}}

    if filters.chart_type == "Bar Chart":
        chart["type"] = "bar"
    else:
        chart["type"] = "line"

    return chart
