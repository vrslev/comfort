frappe.ui.form.on("Delivery Trip", {
  setup(frm) {
    frm.show_submit_message = () => {};

    // Disable "Search" and "Add new Sales Order" buttons in "sales_order" field
    frm.fields_dict.stops.grid.get_docfield("sales_order").only_select = 1;

    // Add query for "sales_order" field
    // that doesn't allow to add orders that have unacceptable status
    // or already in current Trip
    frm.set_query("sales_order", "stops", () => {
      let cur_sales_orders = [];
      frm.doc.stops.forEach((order) => {
        if (order.sales_order) cur_sales_orders.push(order.sales_order);
      });
      return {
        filters: {
          name: ["not in", cur_sales_orders],
          delivery_status: "To Deliver",
        },
      };
    });
  },

  refresh(frm) {
    // Add "Add Multiple" button
    frm.fields_dict.stops.grid.set_multiple_add("sales_order");

    // Duplicate from setup method. Needed here and there.
    frm.fields_dict.stops.grid.get_docfield("sales_order").only_select = 1;

    if (
      !frm.is_new() &&
      frm.doc.docstatus != 2 &&
      frm.doc.status != "Completed"
    ) {
      // TODO: Remove old driver mode
      frm.add_custom_button("Перейти в старый режим водителя", () => {
        location.href = `/driver?name=${frm.doc.name}`;
      });
      frm.add_custom_button(__("Go to Driver mode"), () => {
        location.href = `/app/driver?name=${frm.doc.name}`;
      });
    }

    if (frm.doc.status == "In Progress") {
      frm.page.set_primary_action(__("Complete"), () => {
        if (!frm.doc) {
          throw Error("No doc provided :(");
        }

        frm.call({
          doc: frm.doc,
          method: "set_completed_status",
          callback: () => {
            frappe.show_alert({
              message: __("Delivery Trip completed"),
              indicator: "green",
            });
            frm.reload_doc();
          },
        });
      });
    }
  },
});

frappe.ui.form.on("Delivery Stop", {
  sales_order(frm, cdt, cdn) {
    let doc = frappe.get_doc(cdt, cdn);
    if (!doc.sales_order) return;
    frappe.call({
      method:
        "comfort.stock.doctype.delivery_trip.delivery_trip.get_delivery_and_installation_for_order",
      args: {
        sales_order_name: doc.sales_order,
      },
      callback: (r) => {
        frappe.model.set_value(
          cdt,
          cdn,
          "delivery_type",
          r.message.delivery_type
        );
        frappe.model.set_value(
          cdt,
          cdn,
          "installation",
          r.message.installation
        );
      },
    });
  },

  customer(frm, cdt, cdn) {
    let doc = frappe.get_doc(cdt, cdn);
    frappe.db
      .get_value("Customer", doc.customer, ["address", "city", "phone"])
      .then((r) => {
        frappe.model.set_value(cdt, cdn, "address", r.message.address);
        frappe.model.set_value(cdt, cdn, "city", r.message.city);
        frappe.model.set_value(cdt, cdn, "phone", r.message.phone);
      });
  },
});
