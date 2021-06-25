frappe.ui.form.on('Journal Entry', {
	setup: function (frm) {
		frm.set_query("account", "accounting_entries", function (doc, cdt, cdn) {
			let company = frm.doc.company
			return {
				filters: [
					['Account', 'is_group', '=', 0],
					['Account', 'company', '=', company]
				]
			};
		});
	}
});


