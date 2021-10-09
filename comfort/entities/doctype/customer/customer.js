frappe.ui.form.on("Customer", {
  refresh(frm) {
    // This hides Plus button for PO
    frm.custom_make_buttons = {
      "Purchase Order": "Purchase Order",
    };

    if (frm.doc.vk_url) {
      let btn = frm.add_custom_button(__("Open in VK"), () => {});
      $(btn).attr("onclick", "window.open(cur_frm.doc.vk_url);");
    }
  },
});
