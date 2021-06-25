frappe.ui.form.on('Sales Order', {
	// TODO: Ask if paid to bank or cash
	refresh(frm) {
		if (!frm.is_new() && frm.doc.per_paid < 100) {
			frm.add_custom_button(__('Paid'), () => {
				frappe.prompt({
					label: 'Paid Amount',
					fieldname: 'paid_amount',
					fieldtype: 'Currency',
					options: 'Company:company:default_currency'
				}, (values) => {
					frm.call({
						doc: frm.doc,
						method: 'set_paid',
						args: {
							'paid_amount': values.paid_amount
						},
						default: frm.doc.pending_amount,
						callback: () => {
							frm.reload_doc()
						}
					})
				})
			}).removeClass('btn-default').addClass('btn-primary')
		}

		if (frm.doc.docstatus == 1 && frm.doc.delivery_status != 'Delivered') {
			frm.add_custom_button(__('Delivered'), () => {
				frm.call({
					doc: frm.doc,
					method: 'set_delivered',
					callback: () => {
						frm.reload_doc()
					}
				})
			}).removeClass('btn-default').addClass('btn-primary')
		}
	},
	validate(frm) {
		frm.doc.child_items = []
	}
});

frappe.ui.form.on("Sales Order Item", {
	qty: function (frm, cdt, cdn) {
		calculate_total(frm, cdt, cdn);
	},
	rate: function (frm, cdt, cdn) {
		calculate_total(frm, cdt, cdn);
	},
	item_code: function (frm, cdt, cdn) {
		var child = locals[cdt][cdn];
		if (child.item_code) {
			frappe.db.get_doc('Item', child.item_code)
				.then(doc => {
					frappe.model.set_value(cdt, cdn, 'qty', 1.00)
					frappe.model.set_value(cdt, cdn, 'rate', doc.standard_purchase_rate)
				})
		}
	}
});
var calculate_total = function (frm, cdt, cdn) {
	var child = locals[cdt][cdn];
	frappe.model.set_value(cdt, cdn, "amount", child.qty * child.rate);
}


frappe.ui.form.on("Sales Order Item", "qty", function (frm, cdt, cdn) {
	var sales_item_details = frm.doc.items;
	var total = 0
	for (var i in sales_item_details) {
		total = total + sales_item_details[i].qty
	}
	frm.set_value("total_quantity", total)
});

frappe.ui.form.on("Sales Order Item", "amount", function (frm, cdt, cdn) {
	var sales_item_details = frm.doc.items;
	var total = 0
	for (var i in sales_item_details) {
		total = total + sales_item_details[i].amount
	}
	frm.set_value("total_amount", total)
});
