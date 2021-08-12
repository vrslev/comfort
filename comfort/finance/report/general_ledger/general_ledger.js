frappe.query_reports["General Ledger"] = {
  filters: [
    {
      fieldname: "from_date",
      label: __("From Date"),
      fieldtype: "Date",
      default: frappe.datetime.add_months(frappe.datetime.get_today(), -1),
      reqd: 1,
      width: "60px",
    },
    {
      fieldname: "to_date",
      label: __("To Date"),
      fieldtype: "Date",
      default: frappe.datetime.get_today(),
      reqd: 1,
      width: "60px",
    },
    {
      fieldname: "account",
      label: __("Account"),
      fieldtype: "Link",
      options: "Account",
    },
    {
      fieldname: "customer",
      label: __("Customer"),
      fieldtype: "Link",
      options: "Customer",
    },
    {
      fieldname: "voucher_no",
      label: __("Voucher No"),
      fieldtype: "Data",
    },
  ],
};
