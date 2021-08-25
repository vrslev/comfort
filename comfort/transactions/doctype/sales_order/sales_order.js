// TODO: Know about autoocompletion in JS

comfort.SalesOrderController = frappe.ui.form.Controller.extend({
  setup() {
    this.frm.show_submit_message = () => {}; // Hide "Submit this document to confirm" message
    this.frm.page.sidebar.hide(); // Hide sidebar
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

  setup_buttons() {
    if (!this.frm.is_new() && this.frm.doc.per_paid < 100) {
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
              options: "Cash\nBank",
              default: "Cash",
            },
          ],
          (values) => {
            this.frm.call({
              doc: this.frm.doc,
              method: "add_payment",
              args: {
                paid_amount: values.paid_amount,
                cash: values.account == "Cash",
              },
              callback: () => {
                frappe.show_alert({
                  message: __("Payment added!"),
                  indicator: "green",
                });
              },
            });
          }
        );
      });
    }

    if (this.frm.doc.delivery_status == "To Deliver") {
      this.frm.add_custom_button(__("Add Receipt"), () => {
        frappe.confirm(
          __("Are you sure you want to mark this Sales Order as delivered?"),
          () => {
            this.frm.call({
              doc: this.frm.doc,
              method: "add_receipt",
            });
          }
        );
      });
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
              },
              callback: () => {
                dialog.hide();
                frappe.show_alert({
                  message: __("Combinations are split!"),
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
  },

  refresh() {
    this.setup_buttons();
  },

  onload_post_render() {
    this.setup_quick_add_items();
  },
});

$.extend(cur_frm.cscript, new comfort.SalesOrderController({ frm: cur_frm }));
// DO: Add `add_multiple` to easily add items when From Actual Stock is checked
frappe.ui.form.on("Sales Order", {
  validate(frm) {
    frm.doc.child_items = [];
  },

  commission(frm) {
    if (frm.doc.edit_commission == 1) {
      apply_commission(frm);
    }
  },
  edit_commission(frm) {
    if (frm.doc.edit_commission == 0) {
      apply_commission(frm);
    }
  },

  discount(frm) {
    calculate_total_amount(frm);
  },

  total_amount(frm) {
    frm.set_value(
      "pending_amount",
      frm.doc.total_amount - frm.doc.paid_amount || null
    );
  },

  items_cost(frm) {
    apply_commission(frm);
  },

  service_amount(frm) {
    calculate_total_amount(frm);
  },
});

function calculate_total_amount(frm) {
  frm.set_value(
    "total_amount",
    frm.doc.items_cost +
      frm.doc.margin +
      frm.doc.service_amount -
      frm.doc.discount || null
  );
}

async function apply_commission(frm) {
  await frm.call({
    doc: frm.doc,
    method: "calculate_commission_and_margin",
  });
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
    calculate_total_quantity(frm);
  },

  rate(frm, cdt, cdn) {
    calculate_item_amount(frm, cdt, cdn);
  },

  amount(frm) {
    calculate_items_cost(frm);
  },

  weight(frm, cdt, cdn) {
    calculate_item_total_weight(frm, cdt, cdn);
  },

  total_weight(frm) {
    calculate_total_weight(frm);
  },

  items_remove(frm) {
    recalculate(frm);
  },
});

function calculate_items_cost(frm) {
  if (frm.doc.items && frm.doc.items.length > 0) {
    var total = frm.doc.items
      .map((d) => (d.amount ? d.amount : 0))
      .reduce((a, b) => a + b);
  } else {
    total = null;
  }
  frm.set_value("items_cost", total);
}

function calculate_item_total_weight(frm, cdt, cdn) {
  var doc = frappe.get_doc(cdt, cdn);
  frappe.model.set_value(cdt, cdn, "total_weight", doc.qty * doc.weight);
}

function calculate_total_quantity(frm) {
  if (frm.doc.items && frm.doc.items.length > 0) {
    var qty = frm.doc.items
      .map((d) => (d.amount ? d.qty : 0))
      .reduce((a, b) => a + b);
  } else {
    qty = null;
  }
  frm.set_value("total_quantity", qty);
}

function calculate_item_amount(frm, cdt, cdn) {
  var doc = frappe.get_doc(cdt, cdn);
  frappe.model.set_value(cdt, cdn, "amount", doc.qty * doc.rate);
}

function calculate_total_weight(frm) {
  if (frm.doc.items && frm.doc.items.length > 0) {
    var total = frm.doc.items
      .map((d) => (d.total_weight ? d.total_weight : 0))
      .reduce((a, b) => a + b);
  } else {
    total = null;
  }
  frm.set_value("total_weight", total);
}

function calculate_service_amount(frm) {
  if (frm.doc.services && frm.doc.services.length > 0) {
    var total = frm.doc.services
      .map((d) => (d.rate ? d.rate : 0))
      .reduce((a, b) => a + b);
  } else {
    total = null;
  }
  frm.set_value("service_amount", total);
}

frappe.ui.form.on("Sales Order Service", {
  type(frm, cdt, cdn) {
    var rates = {
      "Delivery to Apartment": 100,
      "Delivery to Entrance": 300,
    };
    let doc = frappe.get_doc(cdt, cdn);
    frappe.model.set_value(cdt, cdn, "rate", rates[doc.type] || 0);
    toggle_services_add_row_btn();
  },

  rate(frm) {
    calculate_service_amount(frm);
  },

  services_remove(frm) {
    calculate_service_amount(frm);
  },
});

function toggle_services_add_row_btn() {
  let btn = cur_frm.fields_dict.services.grid.wrapper.find(".grid-add-row");
  let services_joined = cur_frm.doc.services.map((d) => d.type).join();
  btn.hide();
  if (
    services_joined.match("Delivery") &&
    services_joined.match("Installation")
  ) {
    btn.hide();
  } else {
    btn.show();
  }
}

function recalculate(frm) {
  calculate_items_cost(frm);
  calculate_total_quantity(frm);
  calculate_total_weight(frm);
}

function quick_add_items(text) {
  comfort.get_items(text).then((values) => {
    for (var item of values) {
      let doc = cur_frm.add_child("items", {
        item_code: item.item_code,
        item_name: item.item_name,
        qty: 1,
        rate: item.rate,
        weight: item.weight,
      });
      calculate_item_amount(cur_frm, doc.doctype, doc.name);
      calculate_item_total_weight(cur_frm, doc.doctype, doc.name);
    }

    let grid = cur_frm.fields_dict.items.grid;

    // loose focus from current row
    grid.add_new_row(null, null, true);
    grid.grid_rows[grid.grid_rows.length - 1].toggle_editable_row();

    let grid_rows = grid.grid_rows;
    for (var i = grid_rows.length; i--; ) {
      let doc = grid_rows[i].doc;
      if (!(doc.item_name && doc.item_code)) {
        grid_rows[i].remove();
      }
    }

    recalculate(cur_frm);
    refresh_field("items");
  });
}
