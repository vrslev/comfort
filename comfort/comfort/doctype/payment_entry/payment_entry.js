// Copyright (c) 2020, Shariq and contributors
// For license information, please see license.txt

frappe.ui.form.on('Payment Entry', {
	// refresh: function(frm) {

	// }
	setup: function(frm) {
		frappe.db.get_doc('Company', frm.doc.company)
		.then(doc => {
			if(doc.default_bank_account){
				if(frm.doc.payment_type == 'Pay'){
					frm.set_value('paid_from', doc.default_bank_account);
				}
				else{
					frm.set_value('paid_to', doc.default_bank_account);
				}
			}
			else{
				if(frm.doc.payment_type == 'Pay'){
					frm.set_value('paid_from', doc.default_cash_account);
				}
				else{
					frm.set_value('paid_to', doc.default_cash_account);
				}
			}
			if(frm.doc.payment_type == 'Pay'){
				frm.set_value('paid_to', doc.default_payable_account);
			}
			else{
				frm.set_value('paid_from', doc.default_receivable_account);
			}
		})
	}
});