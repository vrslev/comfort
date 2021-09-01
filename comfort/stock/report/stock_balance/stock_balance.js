frappe.query_reports["Stock Balance"] = {
  filters: [
    {
      fieldname: "stock_type",
      label: __("Stock Type"),
      fieldtype: "Select",
      options:
        "\nAvailable Purchased\nReserved Purchased\nReserved Actual\nAvailable Actual",
      reqd: 1,
    },
  ],
};
