frappe.ui.form.on("Customer", {
  refresh(frm) {
    frm.toolbar.print_icon.hide();
    frm.custom_make_buttons = {
      // This hides Plus button for PO
      "Purchase Order": "Purchase Order",
    };
  },
});
