frappe.ui.form.on('Company', {
	company_name(frm) {
		var company_name = frm.doc.company_name;
		var abbr = company_name.match(/\b(\w)/g).join('');
		frm.set_value('abbr', abbr);
	}
});
