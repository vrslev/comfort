frappe.query_reports["Stock Balance"] = {
  filters: [
    {
      fieldname: "stock_type",
      label: __("Stock Type"),
      fieldtype: "Select",
      options:
        "\nAvailable Purchased\nAvailable Actual\nReserved Purchased\nReserved Actual",
    },
  ],
  formatter(value, row, column, data, original_func) {
    if (column.id == "item_code") {
      column.align = "left";
    }
    return original_func(value, row, column, data);
  },
};
