comfort.SalesOrderController = frappe.ui.form.Controller.extend({
  onload() {
    this.frm.ignore_doctypes_on_cancel_all = [
      "Purchase Return",
      "Sales Return",
      "Checkout",
      "Payment",
      "Purchase Order",
      "Stock Entry",
      "GL Entry",
      "Receipt",
    ];
  },

  setup() {
    this.frm.show_submit_message = () => {};
    this.patch_toolbar_set_page_actions();
    this.add_status_indicators();
    this.setup_make_methods();
  },

  patch_toolbar_set_page_actions() {
    // This hides "Submit" button
    let old_func = cur_frm.toolbar.set_page_actions;
    cur_frm.toolbar.set_page_actions = (status) => {
      old_func.call(cur_frm.toolbar, status);
      if (
        cur_frm.toolbar.current_status == "Submit" &&
        !cur_frm.doc.from_available_stock
      ) {
        cur_frm.toolbar.page.clear_primary_action();
      }
    };
  },

  add_status_indicators() {
    this.frm.page.$title_area.append(
      '<span class="indicator-pill whitespace-nowrap payment-indicator" style="margin-left: 2%;"></span>'
    );
    this.payment_indicator = $(".payment-indicator");
    this.frm.page.$title_area.append(
      '<span class="indicator-pill whitespace-nowrap delivery-indicator" style="margin-left: 2%;"></span>'
    );
    this.delivery_indicator = $(".delivery-indicator");
  },

  setup_make_methods() {
    this.frm.make_methods = {
      Compensation: () => {
        const docname = this.frm.doc.name;
        frappe.new_doc("Compensation", null, () => {
          cur_frm.set_value("voucher_type", "Sales Order");
          cur_frm.set_value("voucher_no", docname);
        });
      },
    };
  },

  refresh() {
    this.setup_buttons();
    this.render_status_indicators();
    this.frm.custom_make_buttons = {
      Payment: "Payment",
      Receipt: "Receipt",
      "Purchase Order": "Purchase Order",
      "Delivery Trip": "Delivery Trip",
    };
    if (this.frm.doc.docstatus == 2) {
      this.frm.custom_make_buttons["Sales Return"] = "Sales Return";
    }
    this.setup_item_query();
  },

  render_status_indicators() {
    this.payment_indicator
      .removeClass()
      .addClass("indicator-pill whitespace-nowrap payment-indicator")
      .html(`<span>${__(this.frm.doc.payment_status)}</span>`)
      .addClass(frappe.utils.guess_colour(this.frm.doc.payment_status));

    this.delivery_indicator
      .removeClass()
      .addClass("indicator-pill whitespace-nowrap delivery-indicator")
      .html(`<span>${__(this.frm.doc.delivery_status)}</span>`)
      .addClass(frappe.utils.guess_colour(this.frm.doc.delivery_status));
  },

  setup_item_query() {
    this.frm.set_query("item_code", "items", () => {
      return {
        query: "comfort.queries.sales_order_item_query",
        filters: {
          from_available_stock: this.frm.doc.from_available_stock,
          from_purchase_order: this.frm.doc.from_purchase_order,
        },
      };
    });
  },

  onload_post_render() {
    this.setup_quick_add_items();
  },

  async setup_buttons() {
    // Add Open in VK button
    let label = __("Open in VK");
    let btn = this.frm.custom_buttons[label];
    let response = await frappe.db.get_value(
      "Customer",
      this.frm.doc.customer,
      "vk_url"
    );
    let msg = await response.message;

    if (msg.vk_url) {
      if (!btn) {
        btn = this.frm.add_custom_button(label, () => {});
      }
      $(btn).attr("onclick", `window.open("${msg.vk_url}");`);
    } else if (btn) {
      btn.hide();
    }

    if (
      !this.frm.is_new() &&
      this.frm.doc.docstatus != 2 &&
      this.frm.doc.per_paid < 100
    ) {
      this.frm.add_custom_button(__("Add Payment"), () => {
        frappe.prompt(
          [
            {
              label: "Paid Amount",
              fieldname: "paid_amount",
              fieldtype: "Currency",
              precision: "0",
              default: this.frm.doc.pending_amount,
            },
            {
              label: "Account",
              fieldname: "account",
              fieldtype: "Select",
              options: [__("Cash"), __("Bank")].join("\n"),
              default: __("Cash"),
            },
          ],
          (values) => {
            this.frm.call({
              doc: this.frm.doc,
              method: "add_payment",
              args: {
                paid_amount: values.paid_amount,
                cash: values.account == __("Cash"),
              },
              callback: () => {
                frappe.show_alert({
                  message: __("Payment added"),
                  indicator: "green",
                });
                this.frm.refresh();
              },
            });
          }
        );
      });
    }

    if (this.frm.doc.delivery_status == "To Deliver") {
      let r = await frappe.call({
        method:
          "comfort.transactions.doctype.sales_order.sales_order.has_linked_delivery_trip",
        args: { sales_order_name: cur_frm.doc.name },
      });
      let has_linked_delivery_stop = await r.message;
      if (!has_linked_delivery_stop) {
        this.frm.add_custom_button(__("Add Receipt"), () => {
          frappe.confirm(
            __("Are you sure you want to mark this Sales Order as delivered?"),
            () => {
              this.frm.call({
                doc: this.frm.doc,
                method: "add_receipt",
                callback: () => {
                  frappe.show_alert({
                    message: __("Receipt added"),
                    indicator: "green",
                  });
                  this.frm.refresh();
                },
              });
            }
          );
        });
      }
    }

    async function copy_to_clipboard_from_endpoint(endpoint) {
      async function get_msg() {
        var r = await cur_frm.call({
          method: endpoint,
          doc: cur_frm.doc,
        });
        return await r.message;
      }

      try {
        navigator.clipboard.write([
          // eslint-disable-next-line no-undef
          new ClipboardItem({ "text/plain": get_msg() }),
        ]);
      } catch (e) {
        // Chrome: https://bugs.chromium.org/p/chromium/issues/detail?id=1014310
        navigator.clipboard.write([
          // eslint-disable-next-line no-undef
          new ClipboardItem({
            "text/plain": new Blob([await get_msg()], { type: "text/plain" }),
          }),
        ]);
      }

      frappe.show_alert({
        indicator: "green",
        message: __("Copied to clipboard."),
      });
    }

    if (!this.frm.is_new() && this.frm.doc.docstatus == 0) {
      this.frm.add_custom_button(__("Check order Message"), () => {
        copy_to_clipboard_from_endpoint("generate_check_order_message");
      });
    }

    if (this.frm.doc.delivery_status == "To Deliver") {
      this.frm.add_custom_button(__("Pickup order Message"), () => {
        copy_to_clipboard_from_endpoint("generate_pickup_order_message");
      });
    }

    function show_check_availability_dialog(response) {
      var fields = [];
      if (response.cannot_add.length > 0) {
        fields.push({
          fieldname: "cannot_add_items",
          fieldtype: "Table",
          cannot_add_rows: true,
          in_place_edit: true,
          label: __("Cannot Add Items"),
          data: response.cannot_add,
          fields: [
            {
              fieldname: "item_code",
              fieldtype: "Link",
              options: "Item",
              in_list_view: 1,
              label: __("Item Code"),
              read_only: 1,
            },
          ],
        });
      }

      if (response.options.length > 0) {
        for (let options of response.options) {
          fields.push({
            fieldname: "unavailable_items",
            fieldtype: "Table",
            label: options.delivery_type,
            cannot_add_rows: true,
            in_place_edit: true,
            data: options.items,
            fields: [
              {
                fieldname: "item_code",
                fieldtype: "Link",
                label: __("Item Code"),
                options: "Item",
                in_list_view: 1,
                read_only: 1,
                columns: 4,
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
            ],
          });
        }
      }

      var dialog = new frappe.ui.Dialog({
        title: __("Unavailable Items"),
        size: "extra-large",
        fields: fields,
        minimizable: 1,
        indicator: "red",
      });

      dialog.fields_list.forEach((field) => {
        // Make tables read only
        field.grid.wrapper.find(".col").unbind("click");
        field.grid.toggle_checkboxes(false);
      });
      dialog.show();
    }

    if (
      !this.frm.is_new() &&
      this.frm.doc.delivery_status == "To Purchase" &&
      !this.frm.doc.from_available_stock
    ) {
      this.frm.add_custom_button(__("Check availability"), () => {
        this.frm.call({
          method: "check_availability",
          doc: this.frm.doc,
          freeze: true,
          callback: (r) => {
            if (r.message) {
              show_check_availability_dialog(r.message);
            }
          },
        });
      });
    }

    function add_grid_button_to_the_right(grid, label, action) {
      let wrapper = grid.wrapper.find('div[class="text-right"]')[0];
      let btn = grid.custom_buttons[label];

      if (!btn) {
        btn = $(
          `<button class="btn btn-xs btn-secondary" style="margin-right: 4px;">${label}</button>`
        )
          .appendTo(wrapper)
          .on("click", action);
        grid.custom_buttons[label] = btn;
      } else {
        btn.removeClass("hidden");
      }
    }

    label = __("Fetch items specs");
    if (
      !this.frm.is_new() &&
      this.frm.doc.docstatus == 0 &&
      !this.frm.doc.from_available_stock
    ) {
      add_grid_button_to_the_right(
        this.frm.fields_dict.items.grid,
        label,
        () => {
          this.frm.call({
            method: "fetch_items_specs",
            doc: this.frm.doc,
            freeze: 1,
          });
        }
      );
    } else {
      let btn = this.frm.fields_dict.items.grid.custom_buttons[label];
      if (btn) {
        btn.addClass("hidden");
      }
    }

    label = __("Split Combinations");
    if (
      this.frm.doc.docstatus == 0 &&
      this.frm.doc.child_items &&
      this.frm.doc.child_items.length > 0
    ) {
      add_grid_button_to_the_right(
        this.frm.fields_dict.items.grid,
        __("Split Combinations"),
        () => {
          const fields = [
            {
              fieldtype: "Link",
              fieldname: "item_code",
              options: "Item",
              in_list_view: 1,
              label: __("Item Code"),
            },
          ];

          var dialog = new frappe.ui.Dialog({
            title: __("Choose combinations to split"),
            size: "large",
            fields: [
              {
                fieldname: "combinations",
                fieldtype: "Table",
                label: __("Combinations"),
                cannot_add_rows: true,
                reqd: 1,
                data: [],
                fields: fields,
              },
            ],
            primary_action_label: __("Save"),
            primary_action: () => {
              this.frm.call({
                doc: this.frm.doc,
                method: "split_combinations",
                freeze: 1,
                args: {
                  combos_docnames: dialog.fields_dict.combinations.grid
                    .get_selected_children()
                    .filter((d) => d.__checked)
                    .map((d) => d.name),
                  save: true,
                },
                callback: () => {
                  dialog.hide();
                  frappe.show_alert({
                    message: __("Combinations are split"),
                    indicator: "green",
                  });
                },
              });
            },
          });

          let parent_items = this.frm.doc.child_items.map(
            (child) => child.parent_item_code
          );
          this.frm.doc.items.forEach((item) => {
            if (parent_items.includes(item.item_code)) {
              dialog.fields_dict.combinations.df.data.push({
                name: item.name,
                item_code: item.item_code,
                item_name: item.item_name,
              });
            }
          });
          dialog.fields_dict.combinations.grid.refresh();

          if (
            !this.frm.doc.child_items ||
            this.frm.doc.child_items.length == 0 ||
            dialog.fields_dict.combinations.grid.data.length == 0
          ) {
            frappe.msgprint("В заказе нет комбинаций");
            return;
          }

          dialog.fields_dict.combinations.grid.display_status = "Read";
          dialog.fields_dict.combinations.grid.grid_buttons.hide();
          dialog.show();
        }
      );
    } else {
      let btn = this.frm.fields_dict.items.grid.custom_buttons[label];
      if (btn) {
        btn.addClass("hidden");
      }
    }

    label = __("Split Order");
    if (this.frm.doc.docstatus == 0) {
      add_grid_button_to_the_right(
        this.frm.fields_dict.items.grid,
        label,
        () => {
          const fields = [
            {
              fieldtype: "Link",
              fieldname: "item_code",
              options: "Item",
              in_list_view: 1,
              label: __("Item Code"),
              columns: 4,
            },
            {
              fieldtype: "Int",
              fieldname: "qty",
              in_list_view: 1,
              label: __("Qty"),
              columns: 1,
            },
          ];

          var dialog = new frappe.ui.Dialog({
            title: __("Choose Items"),
            size: "large",
            fields: [
              {
                fieldname: "items",
                fieldtype: "Table",
                label: __("Items"),
                cannot_add_rows: true,
                reqd: 1,
                data: this.frm.doc.items.map((item) => {
                  return {
                    item_code: item.item_code,
                    item_name: item.item_name,
                    qty: item.qty,
                  };
                }),
                fields: fields,
              },
            ],
            primary_action_label: __("Submit"),
            primary_action: () => {
              this.frm.call({
                method: "split_order",
                doc: this.frm.doc,
                args: {
                  items: dialog.fields_dict.items.grid
                    .get_selected_children()
                    .filter((i) => i.__checked)
                    .map((i) => {
                      return { item_code: i.item_code, qty: i.qty };
                    }),
                },
                callback: (r) => {
                  dialog.hide();
                  if (!r.message) return;

                  console.log(r.message);
                  frappe.dom.freeze();
                  this.frm.reload_doc();
                  frappe.show_alert({
                    message: __("Order is split"),
                    indicator: "green",
                  });
                  frappe.set_route("sales-order", r.message).then(() => {
                    frappe.utils.scroll_to(0);
                    frappe.dom.unfreeze();
                  });
                },
              });
            },
          });

          // dialog.fields_dict.items.grid.display_status = "Read";
          dialog.fields_dict.items.grid.wrapper
            .find('[data-fieldname="item_code"]')
            .unbind("click");
          dialog.fields_dict.items.grid.grid_buttons.hide();
          dialog.show();
        }
      );
    } else {
      let btn = this.frm.fields_dict.items.grid.custom_buttons[label];
      if (btn) {
        btn.addClass("hidden");
      }
    }
  },

  setup_quick_add_items() {
    this.frm.fields_dict.items.$wrapper.unbind("paste").on("paste", (e) => {
      e.preventDefault();
      let clipboard_data =
        e.clipboardData ||
        window.clipboardData ||
        e.originalEvent.clipboardData;
      let pasted_data = clipboard_data.getData("Text");
      if (!pasted_data) return;

      comfort.quick_add_items(
        pasted_data,
        "items",
        (doctype, docname) => {
          calculate_item_amount(cur_frm, doctype, docname);
          calculate_item_total_weight(cur_frm, doctype, docname);
        },
        recalculate_global_item_totals
      );
    });
  },

  commission() {
    if (this.frm.doc.edit_commission == 1) {
      calculate_commission_and_margin();
    }
  },

  edit_commission() {
    if (this.frm.doc.edit_commission == 0) {
      calculate_commission_and_margin();
    }
  },

  discount() {
    calculate_total_amount();
  },

  total_amount() {
    set_per_paid_and_pending_amount();
  },

  items_cost() {
    calculate_commission_and_margin();
  },

  service_amount() {
    calculate_total_amount();
  },
});

function calculate_total_amount() {
  cur_frm.set_value(
    "total_amount",
    cur_frm.doc.items_cost +
      cur_frm.doc.margin +
      cur_frm.doc.service_amount -
      cur_frm.doc.discount || 0
  );
}

function calculate_commission_and_margin() {
  // Using custom method because when user removes items or order in bulk
  // everything goes wrong
  frappe.call({
    method:
      "comfort.transactions.doctype.sales_order.sales_order.calculate_commission_and_margin",
    args: {
      doc: cur_frm.doc,
    },
    callback: (r) => {
      cur_frm.set_value("commission", r.message.commission);
      cur_frm.set_value("margin", r.message.margin);
      calculate_total_amount();
    },
  });
}

function set_per_paid_and_pending_amount() {
  if (
    cur_frm.doc.total_amount == undefined ||
    cur_frm.doc.paid_amount == undefined
  )
    return;

  cur_frm.set_value(
    "pending_amount",
    cur_frm.doc.total_amount - cur_frm.doc.paid_amount
  );

  if (cur_frm.doc.total_amount == 0) {
    var per_paid = 100;
  } else {
    per_paid = (cur_frm.doc.paid_amount / cur_frm.doc.total_amount) * 100;
  }
  cur_frm.set_value("per_paid", per_paid);
}

frappe.ui.form.on("Sales Order Item", {
  item_code(frm, cdt, cdn) {
    var doc = frappe.get_doc(cdt, cdn);
    if (doc.item_code) {
      frappe.db
        .get_value("Item", doc.item_code, ["item_name", "rate", "weight"])
        .then((r) => {
          frappe.model.set_value(cdt, cdn, "qty", 1);
          frappe.model.set_value(cdt, cdn, "item_name", r.message.item_name);
          frappe.model.set_value(cdt, cdn, "rate", r.message.rate);
          frappe.model.set_value(cdt, cdn, "weight", r.message.weight);
        });
    }
  },

  qty(frm, cdt, cdn) {
    calculate_item_amount(frm, cdt, cdn);
    calculate_item_total_weight(frm, cdt, cdn);
    calculate_total_quantity();
  },

  rate(frm, cdt, cdn) {
    calculate_item_amount(frm, cdt, cdn);
  },

  amount() {
    calculate_items_cost();
  },

  weight(frm, cdt, cdn) {
    calculate_item_total_weight(frm, cdt, cdn);
  },

  total_weight() {
    calculate_total_weight();
  },

  items_remove(frm) {
    recalculate_global_item_totals(frm);
  },
});

function calculate_item_total_weight(frm, cdt, cdn) {
  var doc = frappe.get_doc(cdt, cdn);
  frappe.model.set_value(cdt, cdn, "total_weight", doc.qty * doc.weight);
}

function calculate_item_amount(frm, cdt, cdn) {
  var doc = frappe.get_doc(cdt, cdn);
  frappe.model.set_value(cdt, cdn, "amount", doc.qty * doc.rate);
}

function calculate_items_cost() {
  if (cur_frm.doc.items && cur_frm.doc.items.length > 0) {
    var total = cur_frm.doc.items
      .map((d) => (d.amount ? d.amount : 0))
      .reduce((a, b) => a + b);
  } else {
    total = 0;
  }
  cur_frm.set_value("items_cost", total);
}

function calculate_total_quantity() {
  if (cur_frm.doc.items && cur_frm.doc.items.length > 0) {
    var qty = cur_frm.doc.items
      .map((item) => (item.amount ? item.qty : 0))
      .reduce((a, b) => a + b);
  } else {
    qty = null;
  }
  cur_frm.set_value("total_quantity", qty);
}

function calculate_total_weight() {
  if (cur_frm.doc.items && cur_frm.doc.items.length > 0) {
    var total = cur_frm.doc.items
      .map((d) => (d.total_weight ? d.total_weight : 0))
      .reduce((a, b) => a + b);
  } else {
    total = 0;
  }
  cur_frm.set_value("total_weight", total);
}

function recalculate_global_item_totals() {
  calculate_items_cost();
  calculate_total_quantity();
  calculate_total_weight();
}

frappe.ui.form.on("Sales Order Service", {
  type(frm, cdt, cdn) {
    let default_rates = {
      "Delivery to Apartment": 400,
      "Delivery to Entrance": 150,
      Installation: 0,
    };
    let doc = frappe.get_doc(cdt, cdn);
    frappe.model.set_value(cdt, cdn, "rate", default_rates[doc.type]);
    toggle_services_add_row_button();
  },

  rate(frm) {
    calculate_service_amount(frm);
  },

  services_remove(frm) {
    calculate_service_amount(frm);
  },
});

function toggle_services_add_row_button() {
  // If there's both Delivery and Installation services hide "Add Row" button
  let btn = cur_frm.fields_dict.services.grid.wrapper.find(".grid-add-row");
  let services_joined = cur_frm.doc.services.map((d) => d.type).join();
  if (
    services_joined.match("Delivery") &&
    services_joined.match("Installation")
  ) {
    btn.hide();
  } else {
    btn.show();
  }
}

function calculate_service_amount() {
  if (cur_frm.doc.services && cur_frm.doc.services.length > 0) {
    var total = cur_frm.doc.services
      .map((d) => (d.rate ? d.rate : 0))
      .reduce((a, b) => a + b);
  } else {
    total = 0;
  }
  cur_frm.set_value("service_amount", total);
}

$.extend(cur_frm.cscript, new comfort.SalesOrderController({ frm: cur_frm }));
