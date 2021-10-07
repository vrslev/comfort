frappe.ui.form.on("Item", {
  refresh(frm) {
    frm.add_custom_button(__("Fetch specs"), () => {
      comfort.get_items(cur_frm.doc.item_code).then(() => {
        cur_frm.reload_doc();
      });
    });
  },
});
