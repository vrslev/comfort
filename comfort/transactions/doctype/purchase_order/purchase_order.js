comfort.PurchaseOrderController = frappe.ui.form.Controller.extend({
  setup() {
    this.frm.show_submit_message = () => {};
    this.setup_sales_order_query();
    this.setup_make_methods();
  },

  setup_sales_order_query() {
    this.frm.set_query("sales_order_name", "sales_orders", () => {
      let cur_sales_orders = [];
      if (this.frm.doc.sales_orders) {
        this.frm.doc.sales_orders.forEach((order) => {
          if (order.sales_order_name) {
            cur_sales_orders.push(order.sales_order_name);
          }
        });
      }
      return {
        query: "comfort.queries.purchase_order_sales_order_query",
        filters: {
          "not in": cur_sales_orders,
          docname: this.frm.doc.name,
        },
      };
    });

    // Duplicate in refresh
    this.frm.fields_dict.sales_orders.grid.get_docfield(
      "sales_order_name"
    ).only_select = 1;
  },

  setup_make_methods() {
    this.frm.make_methods = {
      Compensation: () => {
        const docname = this.frm.doc.name;
        frappe.new_doc("Compensation", null, () => {
          cur_frm.set_value("voucher_type", "Purchase Order");
          cur_frm.set_value("voucher_no", docname);
        });
      },
    };
  },

  onload_post_render() {
    this.setup_quick_add_items();
    this.frm.fields_dict.sales_orders.grid.set_multiple_add("sales_order_name");
  },

  setup_quick_add_items() {
    this.frm.fields_dict.items_to_sell.$wrapper
      .unbind("paste")
      .on("paste", (e) => {
        e.preventDefault();
        let clipboard_data =
          e.clipboardData ||
          window.clipboardData ||
          e.originalEvent.clipboardData;
        let pasted_data = clipboard_data.getData("Text");
        if (!pasted_data) return;

        comfort.quick_add_items(
          pasted_data,
          "items_to_sell",
          calculate_item_amount
        );
      });
  },

  refresh() {
    this.setup_buttons();
    this.refresh_delivery_options();
    this.frm.custom_make_buttons = {
      Payment: "Payment",
      Checkout: "Checkout",
      Receipt: "Receipt",
    };
    if (this.frm.doc.docstatus == 2) {
      this.frm.custom_make_buttons["Purchase Return"] = "Purchase Return";
    }
    // Duplicate in setup_sales_order_query
    this.frm.fields_dict.sales_orders.grid.get_docfield(
      "sales_order_name"
    ).only_select = 1;
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
      this.frm.add_custom_button(__("Checkout order"), () => {
        if (this.frm.is_dirty()) {
          frappe.msgprint(__("Save Purchase Order before checkout"));
        } else {
          frappe.confirm(
            // prettier-ignore
            __("Current cart in your IKEA account will be replaced with new one. Proceed?"),
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
      this.frm.page.set_primary_action(__("Add Receipt"), () => {
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
                clear_sales_orders_from_localstorage();
                this.frm.refresh();
              },
            });
          }
        );
      });
    }
  },

  refresh_delivery_options() {
    this._render_delivery_options_buttons();

    if (
      this.frm.doc.delivery_options &&
      this.frm.doc.delivery_options.length > 0
    ) {
      this.frm.fields_dict.delivery_options.grid.wrapper
        .find(".grid-add-row")
        .hide();

      if (this.frm.doc.cannot_add_items) {
        this._render_cannot_add_items_button();
      }
    }
  },

  _render_delivery_options_buttons() {
    var fields_dict = cur_frm.fields_dict.delivery_options;
    let el = fields_dict.$wrapper.find(".btn-open-row");
    el.find("a").html(frappe.utils.icon("small-message", "xs"));
    el.find(".edit-grid-row").text(__("Open"));
    $.each(fields_dict.grid.grid_rows, (i) => {
      let row = fields_dict.grid.grid_rows[i];
      row.show_form = () => {
        show_unavailable_items_dialog(row);
      };
    });
  },

  _render_cannot_add_items_button() {
    var grid = this.frm.fields_dict.delivery_options.grid;
    var cannot_add_items = JSON.parse(this.frm.doc.cannot_add_items);
    if (cannot_add_items && cannot_add_items.length > 0) {
      grid.add_custom_button(__("Cannot Add Items"), () => {
        if (this.frm.doc.cannot_add_items) {
          var fake_grid_row = {
            doc: {
              type: __("Cannot Add Items"),
              unavailable_items: JSON.stringify(
                cannot_add_items.map((d) => {
                  return {
                    item_code: d,
                    available_qty: 0,
                  };
                })
              ),
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
              clear_sales_orders_from_localstorage();
              cur_frm.reload_doc();
              resolve();
            },
          });
        }

        frappe.call({
          method: "comfort.integrations.ikea.get_purchase_info",
          args: {
            purchase_id: purchase_id,
            use_lite_id: use_lite_id,
          },
          freeze: true,
          callback: (r) => {
            var args = {
              purchase_id: purchase_id,
              purchase_info: r.message || {},
            };
            if (r.message && Object.keys(r.message).length > 0) {
              _send(args);
            } else {
              frappe.prompt(
                {
                  // prettier-ignore
                  label: __("Can't load information about this order, enter delivery cost"),
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

    function show_enter_purchase_number_dialog() {
      var dialog = new frappe.ui.Dialog({
        title: __("Enter Purchase Number"),
        fields: [
          {
            // prettier-ignore
            label: __("Purchase Number"),
            fieldname: "purchase_id",
            fieldtype: "Int",
            reqd: 1,
          },
        ],

        primary_action({ purchase_id }) {
          add_purchase_info_and_submit(purchase_id, true);
          dialog.hide();
        },
      });
      dialog.no_cancel();
      dialog.show();
    }

    frappe.validated = false;

    this.frm
      .call({ method: "fetch_items_specs", doc: this.frm.doc, freeze: 1 })
      .then(() => {
        frappe.call({
          method: "comfort.integrations.ikea.get_purchase_history",
          freeze: true,
          callback: (r) => {
            if (r.message && r.message.length > 0) {
              let purchases = [];
              r.message.forEach((p) => {
                if (p.status == "IN_PROGRESS") {
                  purchases.push([
                    [p.id, p.datetime_formatted, p.price + " ₽"].join(" | "),
                  ]);
                }
              });

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

                secondary_action_label: __("Enter Purchase Number manually"),
                secondary_action() {
                  show_enter_purchase_number_dialog();
                  dialog.hide();
                },
              });
              dialog.no_cancel();
              dialog.show();
            } else {
              show_enter_purchase_number_dialog();
            }
          },
        });
      });
  },

  delivery_cost() {
    calculate_total_amount();
  },

  sales_orders_cost() {
    calculate_total_amount();
  },

  items_to_sell_cost() {
    calculate_total_amount();
  },
});

function create_unavailable_items_table(response) {
  let orders_to_customers = {};
  if (cur_frm.doc.sales_orders) {
    cur_frm.doc.sales_orders.forEach((o) => {
      orders_to_customers[o.sales_order_name] = o.customer;
    });
  }

  let data = response.map((item) => {
    return {
      item_code: item.item_code,
      item_name: item.item_name,
      parent: item.parent,
      customer: orders_to_customers[item.parent],
      required_qty: item.required_qty,
      available_qty: item.available_qty,
    };
  });

  let fields = [
    {
      fieldname: "item_code",
      fieldtype: "Link",
      options: "Item",
      label: __("Item Code"),
      in_list_view: 1,
      read_only: 1,
      columns: 4,
    },
    {
      fieldname: "parent",
      fieldtype: "Link",
      label: __("Parent"),
      in_list_view: 1,
      read_only: 1,
      options: "Parent",
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
      label: __("Required"),
      in_list_view: 1,
      read_only: 1,
      columns: 1,
    },
    {
      fieldname: "available_qty",
      fieldtype: "Int",
      label: __("Available"),
      in_list_view: 1,
      read_only: 1,
      columns: 1,
    },
  ];

  return {
    fieldname: "unavailable_items",
    fieldtype: "Table",
    label: __("Unavailable Items"),
    cannot_add_rows: true,
    in_place_edit: true,
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
      if (r.message && r.message.length > 0) {
        let title = grid_row.doc.type;
        if (grid_row.doc.service_provider)
          title += ", " + grid_row.doc.service_provider;

        var dialog = new frappe.ui.Dialog({
          title: title,
          size: "extra-large",
          indicator: "red",
          fields: [create_unavailable_items_table(r.message)],
        });
        let grid = dialog.fields_dict.unavailable_items.grid;
        grid.wrapper.find(".col").unbind("click");
        grid.toggle_checkboxes(false);
        dialog.show();
      } else {
        frappe.show_alert(
          {
            message: __("All items are available for this delivery option"),
            indicator: "green",
          },
          1 // seconds
        );
      }
    },
  });
}

function calculate_total_amount() {
  cur_frm.set_value(
    "total_amount",
    (cur_frm.doc.delivery_cost || 0) +
      (cur_frm.doc.items_to_sell_cost || 0) +
      (cur_frm.doc.sales_orders_cost || 0)
  );
}

frappe.ui.form.on("Purchase Order Sales Order", {
  sales_order_name() {
    calculate_total_weight_and_total_weight().then(() => {
      calculate_sales_orders_cost();
    });
  },

  total_amount() {
    calculate_sales_orders_cost();
  },

  sales_orders_remove() {
    calculate_total_weight_and_total_weight().then(() => {
      calculate_sales_orders_cost();
    });
  },
});

function calculate_sales_orders_cost() {
  let sales_orders_cost = 0;
  if (cur_frm.doc.sales_orders) {
    cur_frm.doc.sales_orders.forEach((o) => {
      sales_orders_cost += o.total_amount || 0;
    });
  }
  cur_frm.set_value("sales_orders_cost", sales_orders_cost);
}

function calculate_total_weight_and_total_weight() {
  // Using custom method because when user removes items or order in bulk
  // everything goes wrong
  return frappe.call({
    method:
      "comfort.transactions.doctype.purchase_order.purchase_order.calculate_total_weight_and_total_weight",
    args: {
      doc: cur_frm.doc,
    },
    callback: (r) => {
      cur_frm.set_value("total_weight", r.message[0]);
      cur_frm.set_value("total_margin", r.message[1]);
    },
  });
}

frappe.ui.form.on("Purchase Order Item To Sell", {
  item_code(frm, cdt, cdn) {
    calculate_item_amount(cdt, cdn);
  },

  qty(frm, cdt, cdn) {
    calculate_total_weight_and_total_weight().then(() => {
      calculate_item_amount(cdt, cdn);
    });
  },

  rate(frm, cdt, cdn) {
    calculate_item_amount(cdt, cdn);
  },

  amount() {
    calculate_items_to_sell_cost();
  },

  weight() {
    calculate_total_weight_and_total_weight();
  },

  items_to_sell_remove() {
    calculate_total_weight_and_total_weight().then(() => {
      calculate_items_to_sell_cost();
    });
  },
});

function calculate_item_amount(cdt, cdn) {
  let doc = frappe.get_doc(cdt, cdn);
  if (doc.rate) {
    if (!doc.qty) frappe.model.set_value(cdt, cdn, "qty", 1);
    frappe.model.set_value(cdt, cdn, "amount", (doc.qty || 1) * doc.rate);
  }
}

function calculate_items_to_sell_cost() {
  let items_to_sell = 0;
  if (cur_frm.doc.items_to_sell) {
    cur_frm.doc.items_to_sell.forEach((item) => {
      items_to_sell += item.amount || 0;
    });
  }
  cur_frm.set_value("items_to_sell_cost", items_to_sell);
}

function clear_sales_orders_from_localstorage() {
  if (cur_frm.doc.sales_orders) {
    cur_frm.doc.sales_orders.forEach((s) => {
      frappe.model.remove_from_locals("Sales Order", s.sales_order_name);
    });
  }
}

// Set formatter here because `frm.set_indicator_formatter()` method works only on links
frappe.meta.docfield_map["Purchase Order Delivery Option"].type.formatter =
  function (value, df, options, doc) {
    let color = doc.is_available ? "green" : "red";
    if (!value) return "";
    return `<div class="indicator ${color}">${value}</div>`;
  };

$.extend(
  cur_frm.cscript,
  new comfort.PurchaseOrderController({ frm: cur_frm })
);
