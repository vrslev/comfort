frappe.query_reports["General Ledger"] = {
  filters: [
    {
      fieldname: "from_date",
      label: __("From Date"),
      fieldtype: "Date",
      default: frappe.datetime.add_months(frappe.datetime.get_today(), -1),
      reqd: 1,
    },
    {
      fieldname: "to_date",
      label: __("To Date"),
      fieldtype: "Date",
      default: frappe.datetime.get_today(),
      reqd: 1,
    },
  ],
  formatter: (value, row, column, data, default_formatter) => {
    if (column.id == "voucher_type" && value) {
      return __(value);
    }

    return default_formatter(value, row, column, data);
  },
};
