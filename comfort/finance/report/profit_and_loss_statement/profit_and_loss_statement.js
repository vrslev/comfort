frappe.query_reports["Profit and Loss Statement"] = {
  filters: [
    {
      fieldname: "from_date",
      label: __("From Date"),
      fieldtype: "Date",
      default: frappe.datetime.month_start(),
      reqd: 1,
    },
    {
      fieldname: "to_date",
      label: __("To Date"),
      fieldtype: "Date",
      default: frappe.datetime.month_end(),
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
