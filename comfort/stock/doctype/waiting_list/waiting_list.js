function set_multiple_indicators(doctype, field, get_colors) {
  frappe.meta.docfield_map[doctype][field].formatter = function (
    value,
    df,
    options,
    doc
  ) {
    if (value) {
      var label;
      if (frappe.form.link_formatters[df.options]) {
        label = frappe.form.link_formatters[df.options](value, doc);
      } else {
        label = value;
      }

      const escaped_name = encodeURIComponent(value);

      let parts = [];
      let colors = get_colors(doc || {});
      console.log(colors);
      for (let color of colors) {
        parts.push(`<div class="indicator ${color}"></div>`);
      }
      parts.push(
        `<a href="/app/${frappe.router.slug(
          df.options
        )}/${escaped_name}" data-doctype="${doctype}" data-name="${value}">${label}</a>`
      );
      return parts.join("");
    } else {
      return "";
    }
  };
}

function resolve_color_from_option(option) {
  let status = option[1];
  if (status == "Partially Available") {
    return "yellow";
  } else if (status == "Not Available" || !status) {
    return "red";
  } else {
    return "green";
  }
}

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

    set_multiple_indicators(
      "Waiting List Sales Order",
      "sales_order",
      (doc) => {
        if (doc.current_options == "{}") return ["red"];

        // Schema of doc.current_options:
        // {<option_type>: [<option>, <option>]}
        let all_options = [];
        for (let options of Object.values(JSON.parse(doc.current_options))) {
          for (let option of options) {
            all_options.push(option);
          }
        }

        return all_options.map((option) => {
          return resolve_color_from_option(option);
        });
      }
    );
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
