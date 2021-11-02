frappe.query_reports["Stock Balance"] = {
  filters: [
    {
      fieldname: "stock_type",
      label: __("Stock Type"),
      fieldtype: "Select",
      options:
        "\nAvailable Purchased\nAvailable Actual\nReserved Purchased\nReserved Actual",
      reqd: 1,
    },
  ],
  after_datatable_render() {
    $(".dt-cell--col-1").css("text-align", "left");
  },
};
