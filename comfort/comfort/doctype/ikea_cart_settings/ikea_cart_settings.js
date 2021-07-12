frappe.ui.form.on("Ikea Cart Settings", {
    before_save(frm) {
        if (frm.doc.__unsaved) {
            frappe.call({
                method: "frappe.client.get",
                args: {
                    doctype: frm.doc.doctype,
                    name: frm.doc.name,
                },
                callback(r) {
                    if (r.message) {
                        if (
                            frm.doc.username != r.message.username ||
                            frm.doc.password != r.message.password
                        ) {
                            frm.doc.authorized_token = null;
                            frm.doc.authorized_token_expiration_time = null;
                        }
                    }
                },
            });
        }
    },
});
