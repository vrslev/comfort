frappe.ui.form.on("Waiting List", {
  setup(frm) {
    frm.fields_dict.sales_orders.grid.get_docfield(
      "sales_order"
    ).only_select = 1;

    frm.set_query("sales_order", "sales_orders", () => {
      let cur_sales_orders = [];
      frm.doc.sales_orders.forEach((order) => {
        if (order.sales_order) cur_sales_orders.push(order.sales_order);
      });
      return {
        filters: {
          name: ["not in", cur_sales_orders],
          delivery_status: "To Purchase",
        },
      };
    });

    frm.set_indicator_formatter("sales_order", (doc) => {
      if (!doc.current_options) return "red";

      for (let option of Object.values(JSON.parse(doc.current_options))) {
        let status = option[1];
        if (status == "Partially Available") {
          return "orange";
        } else if (status == "Not Available" || !status) {
          return "red";
        }
      }
      return "green";
    });
  },

  refresh(frm) {
    frm.fields_dict.sales_orders.grid.get_docfield(
      "sales_order"
    ).only_select = 1;

    frm.add_custom_button(__("Get Delivery Services"), () => {
      frm.call({
        doc: frm.doc,
        method: "get_delivery_services",
        freeze: 1,
        callback: () => {
          frappe.show_alert({
            message: __("Delivery Options updated"),
            indicator: "green",
          });
        },
      });
    });
  },
});
