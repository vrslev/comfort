// Copyright (c) 2020, Shariq and contributors
// For license information, please see license.txt

frappe.ui.form.on('Company', {
	// refresh: function(frm) {

	// }
	company_name: function(frm){
		var company_name = frm.doc.company_name;
		var abbr = company_name.match(/\b(\w)/g).join('');
		frm.set_value('abbr', abbr)
	}
});
