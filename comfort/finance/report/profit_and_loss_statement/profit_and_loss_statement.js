frappe.query_reports["Profit and Loss Statement"] = {
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
    value = default_formatter(value, row, column, data);
    if (data && !data.parent_account) {
      // Means it's root
      var $value = $(value).css("font-weight", "bold");
      value = $value.wrap("<p></p>").parent().html();
    }
    return value;
  },
  tree: true,
  name_field: "name",
  parent_field: "parent_account",
};
