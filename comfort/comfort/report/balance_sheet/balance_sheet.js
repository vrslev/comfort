frappe.query_reports["Balance Sheet"] = {
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
      fieldname: "chart_type",
      label: __("Chart_type"),
      fieldtype: "Select",
      options: ["Bar Chart", "Line Chart"],
      default: "Bar Chart",
    },
  ],
  formatter: function (value, row, column, data, default_formatter) {
    if (data && column.fieldname == "account") {
      value = data.account || value;
      column.is_tree = true;
    }

    value = default_formatter(value, row, column, data);

    if (data && !data.parent_account) {
      value = $(`<span>${value}</span>`);

      var $value = $(value).css("font-weight", "bold");
      if (data.warn_if_negative && data[column.fieldname] < 0) {
        $value.addClass("text-danger");
      }

      value = $value.wrap("<p></p>").parent().html();
    }

    return value;
  },
  tree: true,
  name_field: "account",
  parent_field: "parent_account",
  initial_depth: 3,
};
