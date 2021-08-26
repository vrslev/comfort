comfort.IkeaCartController = frappe.ui.form.Controller.extend({
  setup() {
    this.frm.show_submit_message = () => {}; // Hide "Submit this document to confirm" message
    this.frm.page.sidebar.hide(); // Hide sidebar
    this.setup_sales_order_query();
  },

  setup_sales_order_query() {
    this.frm.set_query("sales_order_name", "sales_orders", () => {
      let cur_sales_orders = [];
      this.frm.doc.sales_orders.forEach((order) => {
        if (order.sales_order_name) {
          cur_sales_orders.push(order.sales_order_name);
        }
      });
      return {
        query:
          "comfort.transactions.doctype.purchase_order.purchase_order.sales_order_query",
        filters: {
          "not in": cur_sales_orders,
          docname: this.frm.doc.name,
        },
      };
    });

    this.frm.fields_dict.sales_orders.grid.get_docfield(
      "sales_order_name"
    ).only_select = 1;
  },

  onload_post_render() {
    this.setup_quick_add_items();
    this.frm.fields_dict.sales_orders.grid.set_multiple_add("sales_order_name");
  },

  setup_quick_add_items() {
    this.frm.fields_dict.items_to_sell.grid.wrapper.on("paste", (e) => {
      e.preventDefault();
      let clipboard_data =
        e.clipboardData ||
        window.clipboardData ||
        e.originalEvent.clipboardData;
      let pasted_data = clipboard_data.getData("Text");
      this.quick_add_items(pasted_data);
    });
  },

  refresh() {
    this.setup_buttons();
    this.refresh_delivery_options();
  },

  setup_buttons() {
    if (this.frm.is_new()) {
      return;
    }

    if (this.frm.doc.docstatus == 0) {
      this.frm.add_custom_button(__("Get Delivery Services"), () => {
        this.frm.call({
          doc: this.frm.doc,
          method: "get_delivery_services",
          freeze: 1,
          callback: () => {
            this.refresh_delivery_options();
          },
        });
      });
    }

    if (this.frm.doc.docstatus == 0) {
      this.frm.add_custom_button(__("Checkout"), () => {
        if (this.frm.is_dirty()) {
          frappe.msgprint(__("Save Purchase Order before checkout"));
        } else {
          frappe.confirm(
            __(
              "Current cart in your IKEA account will be replaced with new one. Proceed?"
            ),
            () => {
              this.frm.call({
                doc: this.frm.doc,
                method: "checkout",
                freeze: 1,
                freeze_message: __("Loading items into cart..."),
                callback: () => {
                  window.open("https://www.ikea.com/ru/ru/shoppingcart/");
                },
              });
            }
          );
        }
      });
    }

    if (this.frm.doc.status == "To Receive") {
      this.frm.page.set_primary_action("Add Receipt", () => {
        frappe.confirm(
          __("Are you sure you want to mark this Purchase Order as delivered?"),
          () => {
            this.frm.call({
              doc: this.frm.doc,
              method: "add_receipt",
              callback: () => {
                frappe.show_alert({
                  message: __("Purchase Order completed"),
                  indicator: "green",
                });
                this.frm.refresh();
              },
            });
          }
        );
      });
    }
  },

  refresh_delivery_options() {
    this.render_delivery_options_buttons();

    if (
      this.frm.doc.delivery_options &&
      this.frm.doc.delivery_options.length > 0
    ) {
      this.frm.fields_dict.delivery_options.grid.wrapper
        .find(".grid-add-row")
        .hide();

      if (this.frm.doc.cannot_add_items) {
        this.render_cannot_add_items_button();
      }
    }
  },

  render_delivery_options_buttons() {
    var fields_dict = cur_frm.fields_dict.delivery_options;
    var el = fields_dict.$wrapper.find(".btn-open-row");
    el.find("a").html(frappe.utils.icon("small-message", "xs"));
    el.find(".edit-grid-row").text(__("Open"));
    $.each(fields_dict.grid.grid_rows, (i) => {
      var row = fields_dict.grid.grid_rows[i];
      row.show_form = () => {
        show_unavailable_items_dialog(row);
      };
    });
  },

  render_cannot_add_items_button() {
    var grid = this.frm.fields_dict.delivery_options.grid;

    var cannot_add_items = JSON.parse(this.frm.doc.cannot_add_items);
    if (cannot_add_items.length > 0) {
      grid.add_custom_button(__("Items cannot be added"), () => {
        if (this.frm.doc.cannot_add_items) {
          var fake_grid_row = {
            doc: {
              unavailable_items_json: JSON.stringify(
                cannot_add_items.map((d) => {
                  return {
                    item_code: d,
                    required_qty: 1000,
                    available_qty: 0,
                  };
                })
              ),
              type: __("Items cannot be added"),
            },
          };
          show_unavailable_items_dialog(fake_grid_row);
        }
      });

      grid.wrapper
        .find(".btn-custom")
        .attr("class", "btn btn-xs btn-secondary btn-custom");
    }
  },

  before_submit() {
    function add_purchase_info_and_submit(purchase_id, use_lite_id) {
      return new Promise((resolve) => {
        function _send(args) {
          cur_frm.call({
            doc: cur_frm.doc,
            method: "add_purchase_info_and_submit",
            args: args,
            freeze: 1,
            callback: () => {
              cur_frm.reload_doc();
              resolve();
            },
          });
        }

        frappe.call({
          method: "comfort.comfort_core.ikea.get_purchase_info",
          args: {
            purchase_id: purchase_id,
            use_lite_id: use_lite_id,
          },
          freeze: true,
          callback: (r) => {
            var args = {
              purchase_id: purchase_id,
              purchase_info: r.message,
            };
            if (Object.keys(r.message).length > 0) {
              _send(args);
            } else {
              frappe.prompt(
                {
                  label: __(
                    "Can't load information about this order, enter delivery cost"
                  ),
                  fieldname: "delivery_cost",
                  fieldtype: "Currency",
                  reqd: 1,
                },
                ({ delivery_cost }) => {
                  args.purchase_info.delivery_cost = delivery_cost;
                  _send(args);
                }
              );
            }
          },
        });
      });
    }

    frappe.validated = false;

    frappe.call({
      method: "comfort.comfort_core.ikea.get_purchase_history",
      freeze: true,
      callback: (r) => {
        if (r.message && r.message.length > 0) {
          let purchases = [];
          for (var p of r.message) {
            if (p.status == "IN_PROGRESS") {
              purchases.push([
                [p.id, p.datetime_formatted, p.cost + " ₽"].join(" | "),
              ]);
            }
          }

          var dialog = new frappe.ui.Dialog({
            title: __("Choose order"),
            fields: [
              {
                fieldname: "select",
                fieldtype: "Select",
                in_list_view: 1,
                options: purchases.join("\n"),
              },
            ],

            primary_action({ select }) {
              let purchase_id = /\d+/.exec(select)[0];
              add_purchase_info_and_submit(purchase_id, false);
              dialog.hide();
            },
          });
          dialog.no_cancel();
          dialog.show();
        } else {
          frappe.prompt(
            {
              label: __("Can't receive purchase history, enter order number"),
              fieldname: "purchase_id",
              fieldtype: "Int",
              reqd: 1,
            },
            ({ purchase_id }) => {
              add_purchase_info_and_submit(purchase_id, true);
            }
          );
        }
      },
    });
  },

  quick_add_items(text) {
    comfort.quick_add_items(text, fetch_callback, "items_to_sell");
    for (var i of this.frm.doc.items_to_sell) {
      if (
        !i.item_name ||
        i.item_name == "" ||
        !i.item_code ||
        i.item_code == ""
      ) {
        this.frm.doc.items_to_sell.pop(i);
      }
    }

    function fetch_callback(item_code) {
      frappe.db.get_value(
        "Item",
        item_code,
        ["standard_rate", "item_name", "weight_per_unit"],
        (r) => {
          var child = cur_frm.add_child("items_to_sell");
          frappe.model.set_value(
            child.doctype,
            child.name,
            "item_code",
            item_code
          );
          frappe.model.set_value(
            child.doctype,
            child.name,
            "rate",
            r.standard_rate
          );
          frappe.model.set_value(
            child.doctype,
            child.name,
            "item_name",
            r.item_name
          );
          frappe.model.set_value(
            child.doctype,
            child.name,
            "weight",
            r.weight_per_unit
          );
        }
      );
    }
  },
});

frappe.ui.form.on("Purchase Order Sales Order", {
  sales_order_name(frm, cdt, cdn) {
    let doc = frappe.get_doc(cdt, cdn);
    if (doc.sales_order_name) {
      frappe.db.get_value(
        "Sales Order",
        doc.sales_order_name,
        ["customer", "total_amount"],
        (r) => {
          frappe.model.set_value(cdt, cdn, "customer", r.customer);
          frappe.model.set_value(cdt, cdn, "total", r.total_amount);
        }
      );
    }
  },
});

frappe.ui.form.on("Purchase Order Item To Sell", {
  qty(frm, cdt, cdn) {
    calculate_amount(frm, cdt, cdn);
  },
  rate(frm, cdt, cdn) {
    calculate_amount(frm, cdt, cdn);
  },
  item_code(frm, cdt, cdn) {
    calculate_amount(frm, cdt, cdn);
  },
});

function calculate_amount(frm, cdt, cdn) {
  var doc = frappe.get_doc(cdt, cdn);
  if (doc.rate) {
    if (!doc.qty) doc.qty = 1;
    doc.amount = doc.rate * doc.qty;
    frm.refresh_fields();
  }
}

function create_unavailable_items_table(response) {
  var orders_to_customers = {};
  for (var order of cur_frm.doc.sales_orders) {
    orders_to_customers[order.sales_order_name] = order.customer;
  }

  var data = [];
  for (var item of response) {
    data.push({
      item_code: item.item_code,
      item_name: item.item_name,
      parent: item.parent,
      customer: orders_to_customers[item.parent],
      required_qty: item.required_qty,
      available_qty: item.available_qty,
    });
  }

  var fields = [
    {
      fieldname: "item_code",
      fieldtype: "Link",
      options: "Item",
      in_list_view: 1,
      label: "Артикул",
      columns: 4,
      read_only: 1,
    },
    {
      fieldname: "parent",
      fieldtype: "Link",
      label: "Parent",
      in_list_view: 1,
      options: "Parent",
      read_only: 1,
      formatter: (value, df, options, doc) => {
        if (value && doc.customer) {
          return `<a href="/app/sales-order/${value}" data-doctype="Sales Order" data-name="${value}">
				${value}: ${doc.customer}</a>`;
        } else if (value) {
          return value;
        } else {
          return;
        }
      },
    },
    {
      fieldname: "required_qty",
      fieldtype: "Int",
      label: "Required",
      in_list_view: 1,
      read_only: 1,
      columns: 1,
    },
    {
      fieldname: "available_qty",
      fieldtype: "Int",
      label: "Available",
      in_list_view: 1,
      read_only: 1,
      columns: 1,
    },
  ];

  return {
    fieldname: "unavailable_items",
    fieldtype: "Table",
    cannot_add_rows: true,
    in_place_edit: true,
    label: __("Unavailable Items"),
    data: data,
    fields: fields,
  };
}

function show_unavailable_items_dialog(grid_row) {
  cur_frm.call({
    doc: cur_frm.doc,
    method: "get_unavailable_items_in_cart_by_orders",
    args: {
      unavailable_items: grid_row.doc.unavailable_items,
    },
    callback: (r) => {
      if (!Array.isArray(r.message)) {
        r.message = [r.message];
      }
      if (r.message && r.message.length > 0) {
        var title = grid_row.doc.type;
        if (grid_row.doc.service_provider) {
          title += ", " + grid_row.doc.service_provider;
        }
        var dialog = new frappe.ui.Dialog({
          title: title,
          size: "extra-large",
          fields: [create_unavailable_items_table(r.message)],
          indicator: "red",
        });
        let grid = dialog.fields_dict.unavailable_items.grid;
        grid.wrapper.find(".col").unbind("click");
        grid.toggle_checkboxes(false);
        dialog.show();
      } else {
        frappe.show_alert({
          message: "При этом способе доставки все товары есть в наличии",
          indicator: "green",
        });
      }
    },
  });
}

function show_items_cannot_be_added_dialog() {
  // TODO: Items cannot be added dialog
  var cannot_add_items = JSON.parse(cur_frm.doc.cannot_add_items);
  cannot_add_items = cannot_add_items.map((d) => {
    return {
      item_code: d,
      required_qty: 1000,
      available_qty: 0,
    };
  });
  var grid_row = {};
  grid_row.doc = {};
  grid_row.doc.unavailable_items_json = JSON.stringify(cannot_add_items);
  grid_row.doc.type = __("Items cannot be added");
  show_unavailable_items_dialog(grid_row);
}
$.extend(cur_frm.cscript, new comfort.IkeaCartController({ frm: cur_frm }));
