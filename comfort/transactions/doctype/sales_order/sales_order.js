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

  refresh() {
    this.setup_buttons();
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

    if (
      this.frm.doc.docstatus == 0 &&
      this.frm.doc.child_items &&
      this.frm.doc.child_items.length > 0
    ) {
      this.frm.add_custom_button(__("Split Combinations"), () => {
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
          fields: [
            {
              fieldname: "combinations",
              fieldtype: "Table",
              label: "Combinations",
              cannot_add_rows: true,
              size: "large",
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
      });
    }

    if (!this.frm.is_new() && this.frm.doc.docstatus == 0) {
      this.frm.add_custom_button(__("Check order Message"), () => {
        this.frm.call({
          method: "generate_check_order_message",
          doc: this.frm.doc,
          callback: (r) => {
            if (r.message) {
              copy_to_clipboard(r.message);
            }
          },
        });
      });
    }

    if (this.frm.doc.delivery_status == "To Deliver") {
      this.frm.add_custom_button(__("Pickup order Message"), () => {
        this.frm.call({
          method: "generate_pickup_order_message",
          doc: this.frm.doc,
          callback: (r) => {
            if (r.message) {
              copy_to_clipboard(r.message);
            }
          },
        });
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
      this.frm.doc.docstatus == 0 &&
      !this.frm.doc.from_available_stock
    ) {
      this.frm.add_custom_button(__("Check availability"), () => {
        this.frm.call({
          method: "check_availability",
          doc: this.frm.doc,
          freeze: true,
          callback: (r) => {
            // console.log(r.message);
            if (r.message) {
              show_check_availability_dialog(r.message);
            }
          },
        });
      });
    }

    let grid = this.frm.fields_dict.items.grid;
    let label = __("Fetch items specs");

    if (
      !this.frm.is_new() &&
      this.frm.doc.docstatus == 0 &&
      !this.frm.doc.from_available_stock
    ) {
      // Add "Fetch items specs" button
      let wrapper = grid.wrapper.find('div[class="text-right"]')[0];

      let action = () => {
        this.frm.call({
          method: "fetch_items_specs",
          doc: this.frm.doc,
          freeze: 1,
        });
      };

      let btn = grid.custom_buttons[label];
      if (!btn) {
        btn = $(
          `<button class="btn btn-xs btn-secondary style="margin-right: 4px;">${label}</button>`
        )
          .appendTo(wrapper)
          .on("click", action);
        grid.custom_buttons[label] = btn;
      } else {
        btn.removeClass("hidden");
      }
    } else {
      let btn = grid.custom_buttons[label];
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

      quick_add_items(pasted_data);
    });
  },

  commission() {
    if (this.frm.doc.edit_commission == 1) {
      apply_commission_and_margin();
    }
  },

  edit_commission() {
    if (this.frm.doc.edit_commission == 0) {
      apply_commission_and_margin();
    }
  },

  discount() {
    calculate_total_amount();
  },

  total_amount() {
    set_per_paid_and_pending_amount();
  },

  items_cost() {
    apply_commission_and_margin();
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

function apply_commission_and_margin() {
  cur_frm.call({
    doc: cur_frm.doc,
    method: "calculate_commission_and_margin",
    callback: () => {
      calculate_total_amount();
    },
  });
}

function set_per_paid_and_pending_amount() {
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
      "Delivery to Apartment": 300,
      "Delivery to Entrance": 100,
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
  // TODO: Doesn't work
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

function quick_add_items(text) {
  comfort.get_items(text).then((values) => {
    for (var v of values) {
      let doc = cur_frm.add_child("items", {
        item_code: v.item_code,
        item_name: v.item_name,
        qty: 1,
        rate: v.rate,
        weight: v.weight,
      });
      calculate_item_amount(cur_frm, doc.doctype, doc.name);
      calculate_item_total_weight(cur_frm, doc.doctype, doc.name);
    }

    let grid = cur_frm.fields_dict.items.grid;

    // loose focus from current row
    grid.add_new_row(null, null, true);
    grid.grid_rows[grid.grid_rows.length - 1].toggle_editable_row();

    for (var i = grid.grid_rows.length; i--; ) {
      let doc = grid.grid_rows[i].doc;
      if (!(doc.item_name && doc.item_code)) {
        grid.grid_rows[i].remove();
      }
    }

    recalculate_global_item_totals(cur_frm);
    refresh_field("items");
  });
}

function copy_to_clipboard(message) {
  let input = $("<textarea>");
  $("body").append(input);
  input.val(message).select();

  document.execCommand("copy");
  input.remove();

  frappe.show_alert({
    indicator: "green",
    message: __("Copied to clipboard."),
  });
}

$.extend(cur_frm.cscript, new comfort.SalesOrderController({ frm: cur_frm }));
