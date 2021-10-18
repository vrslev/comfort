frappe.ui.form.on("Item", {
  refresh(frm) {
    frm.add_custom_button(__("Fetch specs"), () => {
      comfort.get_items(frm.doc.item_code).then(() => {
        frm.reload_doc();
        frappe.show_alert({
          message: __("Information about item updated"),
          indicator: "Green",
        });
      });
    });

    frm.custom_make_buttons = {
      "Sales Order": "Sales Order",
      "Sales Return": "Sales Return",
      "Purchase Order": "Purchase Order",
      "Purchase Return": "Purchase Return",
    };
  },
});
