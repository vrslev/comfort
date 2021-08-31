frappe.ui.form.on("Customer", {
  refresh(frm) {
    // This hides Plus button for PO
    frm.custom_make_buttons = {
      "Purchase Order": "Purchase Order",
    };
  },
});
