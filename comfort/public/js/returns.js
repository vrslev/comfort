comfort.ReturnController = frappe.ui.form.Controller.extend({
  setup() {
    this.patch_toolbar_set_page_actions();

    frappe.ui.form.on(`${this.frm.doctype} Item`, {
      items_remove(frm) {
        frm.call({ doc: frm.doc, method: "calculate" });
      },
    });
  },

  refresh() {
    this.frm.fields_dict.items.grid.grid_buttons
      .find(".grid-add-row")
      .unbind("click")
      .on("click", () => {
        show_add_row_dialog();
      });
  },

  patch_toolbar_set_page_actions() {
    let old_func = this.frm.toolbar.set_page_actions;
    this.frm.toolbar.set_page_actions = (status) => {
      old_func.call(this.frm.toolbar, status);
      if (this.frm.toolbar.current_status == "Cancel") {
        this.frm.toolbar.page.clear_secondary_action();
      }
    };
  },
});

async function show_add_row_dialog() {
  var data;
  await cur_frm.call({
    doc: cur_frm.doc,
    method: "get_items_available_to_add",
    callback: (r) => (data = r.message),
  });
  if (!data) return frappe.show_alert(__("No items to add available"));

  var dialog = new frappe.ui.Dialog({
    title: __("Choose Items"),
    size: "large",
    fields: [
      {
        fieldname: "items",
        fieldtype: "Table",
        label: "Items",
        cannot_add_rows: true,
        reqd: 1,
        data: data,
        fields: [
          {
            fieldtype: "Link",
            fieldname: "item_code",
            label: __("Item Code"),
            options: "Item",
            in_list_view: 1,
            read_only: 1,
          },
          {
            fieldtype: "Int",
            fieldname: "qty",
            label: __("Quantity"),
            in_list_view: 1,
          },
        ],
      },
    ],
    primary_action_label: __("Add"),
    primary_action: () => {
      let selected_items = dialog.fields_dict.items.grid
        .get_selected_children()
        .filter((item) => item.__checked);
      if (selected_items.length == 0)
        return frappe.show_alert(__("Choose items first"));

      cur_frm.call({
        doc: cur_frm.doc,
        method: "add_items",
        args: {
          items: selected_items,
        },
        callback: (r) => {
          if (r.exc) return;

          frappe.show_alert({
            message: __("Items added"),
            indicator: "green",
          });
          cur_frm.dirty();
          dialog.hide();
        },
      });
    },
  });

  dialog.$body.prepend(
    // prettier-ignore
    `<p class="frappe-confirm-message">${
      __("You can also change quantity as you want.")
    }</p>`
  );
  let grid = dialog.fields_dict.items.grid;
  grid.grid_buttons.hide();
  grid.wrapper.find('[data-fieldname="item_code"]').unbind("click");
  grid.refresh();
  dialog.show();
}
