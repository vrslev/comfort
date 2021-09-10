frappe.provide("comfort");

frappe.ui.form.on("Purchase Return", {
  refresh(frm) {
    frm.custom_make_buttons = {
      "Sales Return": "Sales Return",
    };
  },
});

$.extend(this.frm.cscript, new comfort.ReturnController({ frm: this.frm }));
