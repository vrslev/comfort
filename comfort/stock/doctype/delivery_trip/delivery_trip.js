frappe.ui.form.on("Delivery Trip", {
  setup(frm) {
    frm.show_submit_message = () => {};
    frm.page.sidebar.hide();

    frm.fields_dict.stops.grid.get_docfield("sales_order").only_select = 1;
    frm.set_query("sales_order", "stops", () => {
      let cur_sales_orders = [];
      frm.doc.stops.forEach((order) => {
        if (order.sales_order) cur_sales_orders.push(order.sales_order);
      });
      return {
        filters: {
          name: ["not in", cur_sales_orders],
          docstatus: ["!=", 2],
        },
      };
    });
  },

  refresh(frm) {
    if (
      !frm.is_new() &&
      frm.doc.docstatus != 2 &&
      frm.doc.status != "Completed"
    ) {
      frm.add_custom_button(__("Send Telegram message"), () => {
        frm.call({
          doc: frm.doc,
          method: "render_telegram_message",
          freeze: 1,
          callback: (r) => {
            var dialog = new frappe.ui.Dialog({
              title: __("Preview"),
              primary_action_label: __("Send"),
              primary_action: () => {
                frappe.call({
                  method:
                    "comfort.stock.doctype.delivery_trip.delivery_trip.send_telegram_message",
                  args: {
                    text: r.message,
                  },
                  freeze: 1,
                  callback: () => {
                    frappe.show_alert({
                      message: __("Message sent!"),
                      indicator: "green",
                    });
                    dialog.hide();
                  },
                });
              },
            });
            dialog.$body.append(
              `<p class="frappe-confirm-message">${r.message}</p>`
            );
            dialog.show();
          },
        });
      });
    }

    if (frm.doc.status == "In Progress") {
      frm.page.set_primary_action(__("Complete"), () => {
        frm.set_value("status", "Completed");
        frm.save("Update");
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
