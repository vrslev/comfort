frappe.provide("comfort");

comfort.IkeaCartController = frappe.ui.form.Controller.extend({
  setup() {
    this.setup_sales_order_query();
  },

  setup_sales_order_query() {
    this.frm.set_query("sales_order_name", "sales_orders", () => {
      var cur_sales_orders = [];
      this.frm.doc.sales_orders.forEach((d) => {
        if (d.sales_order_name) {
          cur_sales_orders.push(d.sales_order_name);
        }
      });
      return {
        query:
          "comfort.transactions.doctype.purchase_order.purchase_order.sales_order_query",
        filters: {
          "not in": cur_sales_orders,
        },
      };
    });
    this.frm.fields_dict.sales_orders.grid.get_docfield(
      "sales_order_name"
    ).only_select = 1;
  },

  onload_post_render() {
    this.frm.fields_dict.items_to_sell.grid.wrapper.on("paste", (e) => {
      e.preventDefault();
      let clipboard_data =
        e.clipboardData ||
        window.clipboardData ||
        e.originalEvent.clipboardData;
      let pasted_data = clipboard_data.getData("Text");
      this.quick_add_items(pasted_data);
    });

    this.frm.fields_dict.sales_orders.grid.set_multiple_add("sales_order_name");
  },

  refresh() {
    if (this.frm.doc.docstatus == 0 && !this.frm.doc.__islocal) {
      this.frm.add_custom_button(__("Update Delivery Services"), () => {
        this.frm.doc.__unsaved = 1;
        this.frm.save();
      });

      this.frm.add_custom_button(__("Checkout On IKEA Site"), () => {
        if (this.frm.doc.__unsaved) {
          frappe.msgprint("Чтобы оформить заказ, необходимо сохранить корзину");
        } else {
          frappe.confirm(
            "Нынешняя корзина пропадёт. Всё равно продолжить?",
            () => {
              this.frm.call({
                doc: this.frm.doc,
                method: "checkout",
                freeze: 1,
                freeze_message: "Загружаю товары в корзину...",
                callback: () => {
                  window.open("https://www.ikea.com/ru/ru/shoppingcart/");
                },
              });
            }
          );
        }
      });
    }

    if (!this.frm.is_new() && this.frm.doc.status == "To Receive") {
      this.frm.page.set_primary_action("Received", () => {
        this.frm.call({
          method: "create_receipt",
          doc: this.frm.doc,
          callback: () => {
            frappe.show_alert({
              message: __("Purchase Order completed"),
              indicator: "green",
            });
            this.frm.refresh();
          },
        });
      });
    }

    // if (this.frm.doc.status == 'To Receive') {
    if (this.frm.doc.status == "Draft") {
      this.frm.fields_dict.items_to_sell.grid
        .add_custom_button(__("Create Sales Order"), () => {
          const fields = [
            {
              fieldtype: "Link",
              fieldname: "item_code",
              options: "Item",
              in_list_view: 1,
              read_only: 1,
              formatter: (value, df, options, doc) => {
                // to delete links
                if (
                  doc &&
                  value &&
                  doc.item_name &&
                  doc.item_name !== value &&
                  doc.item_code === value
                ) {
                  return value + ": " + doc.item_name;
                } else if (!value && doc.doctype && doc.item_name) {
                  return doc.item_name;
                } else {
                  return value;
                }
              },
              label: __("Item Code"),
            },
            {
              fieldtype: "Int",
              fieldname: "qty",
              in_list_view: 1,
              columns: 1,
              label: __("Qty"),
            },
          ];

          var dialog = new frappe.ui.Dialog({
            title: __("Choose Items for new Sales Order"),
            fields: [
              {
                fieldname: "customer",
                fieldtype: "Link",
                label: "Customer",
                options: "Customer",
                reqd: 1,
                only_select: 1,
              },
              {
                fieldtype: "Column Break",
              },
              {
                fieldtype: "Section Break",
              },
              {
                fieldname: "items",
                fieldtype: "Table",
                label: "Items",
                cannot_add_rows: true,
                reqd: 1,
                data: [],
                fields: fields,
              },
            ],
            size: "large",
            primary_action: (data) => {
              console.log(data);
              var selected_items = data.items
                .filter((d) => d.__checked)
                .map((d) => {
                  return {
                    item_code: d.item_code,
                    qty: d.qty,
                    rate: d.rate, // TODO: Need to fix rate. Somehow force it
                  };
                });
              // let selected =
              //   dialog.fields_dict.items.grid.get_selected_children();
              // selected = selected.filter((d) => d.__checked);

              this.frm.call({
                doc: this.frm.doc,
                method: "create_new_sales_order_from_items_to_sell",
                args: {
                  items: selected_items,
                  customer: data.customer,
                },
                // callback:
              });
              // for (var d of selected) {

              // }
              dialog.hide();
            },
            primary_action_label: __("Choose"),
          });

          dialog.fields_dict.items.df.data = this.frm.doc.items_to_sell.map(
            (d) => {
              return {
                name: d.name,
                item_code: d.item_code,
                item_name: d.item_name,
                qty: d.qty,
                rate: d.rate,
              };
            }
          );

          let grid = dialog.fields_dict.items.grid;
          grid.grid_buttons.hide();
          grid.refresh();
          grid.wrapper.find('[data-fieldname="item_code"]').unbind("click");

          dialog.show();
        })
        .attr("class", "btn btn-xs btn-secondary btn-custom");
    }

    this.render_unavailable_items_buttons();

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

  render_unavailable_items_buttons() {
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
    function before_submit_events(purchase_id, use_lite_id = false) {
      return new Promise((resolve) => {
        frappe.call({
          method:
            "comfort.transactions.doctype.purchase_order.purchase_order.get_purchase_info",
          freeze: true,
          args: {
            purchase_id: purchase_id,
            use_lite_id: use_lite_id,
          },
          callback: (res) => {
            if (res.message) {
              var args = res.message;
              args.purchase_id = purchase_id;

              if (!res.message.purchase_info_loaded) {
                frappe.prompt(
                  {
                    label:
                      "Не удалось загрузить информацию о заказе. Введите стоимость доставки",
                    fieldname: "delivery_cost",
                    fieldtype: "Currency",
                    reqd: 1,
                  },
                  ({ delivery_cost }) => {
                    args.delivery_cost = delivery_cost;
                    cur_frm.call({
                      method: "add_purchase_info_and_submit",
                      doc: cur_frm.doc,
                      args: args,
                      freeze: 1,
                      callback: () => {
                        cur_frm.reload_doc();
                        resolve();
                      },
                    });
                  }
                );
              } else {
                cur_frm.call({
                  method: "add_purchase_info_and_submit",
                  doc: cur_frm.doc,
                  args: args,
                  freeze: 1,
                  callback: () => {
                    cur_frm.reload_doc();
                    resolve();
                  },
                });
              }
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
        if (r.message) {
          var select_data = [];
          for (var p of r.message) {
            if (p.status == "IN_PROGRESS") {
              select_data.push([
                [p.id, p.datetime_formatted, p.cost + " ₽"].join(" | "),
              ]);
            }
          }
          var dialog = new frappe.ui.Dialog({
            title: "Выберите заказ",
            fields: [
              {
                fieldname: "select",
                fieldtype: "Select",
                in_list_view: 1,
                options: select_data.join("\n"),
              },
            ],

            primary_action(v) {
              var purchase_id = /\d+/.exec(v.select)[0];
              before_submit_events(purchase_id);
            },
          });
          dialog.no_cancel();
          dialog.show();
        } else {
          frappe.prompt(
            {
              label:
                "Не удалось получить историю покупок. Введите номер заказа",
              fieldname: "purchase_id",
              fieldtype: "Int",
              reqd: 1,
            },
            ({ purchase_id }) => {
              before_submit_events(purchase_id, true);
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
