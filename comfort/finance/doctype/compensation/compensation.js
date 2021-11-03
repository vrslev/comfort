frappe.ui.form.on("Compensation", {
  setup(frm) {
    frm.show_submit_message = () => {};

    // Disable "Search" and "Add new {}" buttons in "voucher_no" field
    frm.get_docfield("voucher_no").only_select = 1;

    frm.get_docfield("voucher_no").get_query = () => {
      return {
        filters: {
          docstatus: 1,
        },
      };
    };
  },
  refresh(frm) {
    frm.get_docfield("voucher_no").only_select = 1;

    if (frm.doc.status == "Draft") {
      frm.page.set_primary_action(__("Received"), () => frm.savesubmit());
    }
  },
});
