frappe.listview_settings["Delivery Trip"] = {
  add_fields: ["status"],
  get_indicator: (doc) => {
    if (["Cancelled", "Draft"].includes(doc.status)) {
      return [__(doc.status), "red"];
    } else if (doc.status == "In Progress") {
      return [__(doc.status), "orange"];
    } else if (doc.status === "Completed") {
      return [__(doc.status), "green"];
    }
  },
};

frappe.listview_settings["Purchase Order"] = {
  add_fields: ["status"],
  get_indicator: (doc) => {
    if (["Cancelled", "Draft"].includes(doc.status)) {
      return [__(doc.status), "red"];
    } else if (doc.status == "To Receive") {
      return [__(doc.status), "orange"];
    } else if (doc.status === "Completed") {
      return [__(doc.status), "green"];
    }
  },
};

frappe.listview_settings["Sales Order"] = {
  add_fields: ["status"],
  get_indicator: (doc) => {
    if (["Cancelled", "Draft"].includes(doc.status)) {
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
    list.page.set_secondary_action(
      __("Add Sales Order from Available Stock"),
      () => {
        frappe.prompt(
          {
            label: __("Stock Type"),
            fieldname: "stock_type",
            fieldtype: "Select",
            options: "Available Purchased\nAvailable Actual",
            reqd: 1,
            default: "Available Purchased",
          },
          ({ stock_type }) => {
            function create_doc(purchase_order) {
              let data = { from_available_stock: stock_type };
              if (purchase_order) {
                data.from_purchase_order = purchase_order;
              }
              frappe
                .call({
                  method:
                    "comfort.transactions.doctype.sales_order.sales_order.validate_from_available_stock_params",
                  args: data,
                })
                .then(() => {
                  frappe.new_doc("Sales Order", data);
                });
            }

            if (stock_type == "Available Purchased") {
              frappe.prompt(
                {
                  label: __("Purchase Order"),
                  fieldname: "purchase_order",
                  fieldtype: "Link",
                  options: "Purchase Order",
                  reqd: 1,
                  only_select: 1,
                },
                ({ purchase_order }) => create_doc(purchase_order),
                __("Choose Purchase Order")
              );
            } else {
              create_doc();
            }
          },
          __("Choose Stock Type")
        );
      },
      "small-add"
    );
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
  function clear_not_in_po_filter() {
    list.filter_area.filter_list.filters
      .filter((d) => d.fieldname == "name" && d.condition == "in")
      .forEach((d) => d.remove());
  }

  clear_not_in_po_filter();
  list.filter_area.filter_list.apply();

  async function change() {
    clear_not_in_po_filter();

    if (check.get_value() == 1) {
      await frappe.call({
        method:
          "comfort.transactions.doctype.sales_order.sales_order.get_sales_orders_not_in_purchase_order",
        callback: (r) => {
          list.filter_area.filter_list.add_filter(
            "Sales Order",
            "name",
            "in",
            r.message,
            true
          );
        },
      });
    }
    list.filter_area.filter_list.on_change();
  }

  var check = list.page.add_field(
    {
      label: __("Not in Purchase Order"),
      fieldname: "not_in_po",
      fieldtype: "Check",
      change() {
        change();
      },
    },
    list.filter_area.standard_filters_wrapper
  );

  check.$input.unbind("input"); // To avoid duplicate calls
  delete list.page.fields_dict["not_in_po"]; // To skip main call for all items
}

frappe.listview_settings["Customer"] = {
  hide_name_column: true,
};

frappe.listview_settings["Item"] = {
  hide_name_column: true,
};
