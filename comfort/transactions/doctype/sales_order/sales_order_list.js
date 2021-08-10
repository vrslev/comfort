frappe.listview_settings["Sales Order"] = {
  add_fields: ["status"],
  get_indicator: function (doc) {
    if (in_list(["Cancelled", "Draft"], doc.status)) {
      return [__(doc.status), "red"];
    } else if (doc.status == "In Progress") {
      return [__(doc.status), "orange"];
    } else if (doc.status === "Completed") {
      return [__(doc.status), "green"];
    }
  },
  onload(list) {
    substitute_status_colours();
    add_not_in_po_check(list);
    list.page.sidebar.remove();
  },
};

function substitute_status_colours() {
  var old_guess_colour = frappe.utils.guess_colour;
  frappe.utils.guess_colour = (text) => {
    var colors = {
      "In Progress": "orange",
      Completed: "green",
      "To Purchase": "red",
      Purchased: "orange",
      "To Deliver": "orange",
      Delivered: "green",
      Unpaid: "red",
      "Partially Paid": "orange",
      Paid: "green",
      Overpaid: "orange",
      "": " ",
    };
    if (colors[text]) {
      return colors[text];
    } else {
      return old_guess_colour(text);
    }
  };
}

function add_not_in_po_check(list) {
  function clear_not_in_po_filter(refresh) {
    list.filter_area.filter_list.filters
      .filter((d) => d.fieldname == "name" && d.condition == "not in")
      .forEach((d) => d.remove());
    if (refresh) {
      list.filter_area.filter_list.apply();
    }
  }

  clear_not_in_po_filter(true);

  var check = list.page.add_field(
    {
      label: __("Not in Purchase Order"),
      fieldname: "not_in_po",
      fieldtype: "Check",
      async change() {
        clear_not_in_po_filter();

        if (check.get_value() == 1) {
          await frappe.call({
            method:
              "comfort.transactions.doctype.sales_order.sales_order.get_sales_orders_in_purchase_order",
            callback: (r) => {
              list.filter_area.filter_list.add_filter(
                "Sales Order",
                "name",
                "not in",
                r.message,
                true
              );
            },
          });
        }
        list.filter_area.filter_list.on_change();
      },
    },
    list.filter_area.standard_filters_wrapper
  );

  check.$input.unbind("input"); // To avoid duplicate calls
  delete list.page.fields_dict["not_in_po"]; // To skip main call for all items
}
