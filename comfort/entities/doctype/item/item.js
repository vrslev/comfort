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
  },
});
