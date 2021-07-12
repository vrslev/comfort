frappe.ui.form.on("Item", {
    setup(frm) {
        frm.set_query("item_code", "child_items", () => {
            return {
                filters: {
                    name: ["!=", frm.doc.name],
                },
            };
        });
    },
});
