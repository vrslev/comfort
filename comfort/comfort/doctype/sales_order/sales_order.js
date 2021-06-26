frappe.ui.form.on('Sales Order', {
	// TODO: Ask if paid to bank or cash
	refresh(frm) {
		if (!frm.is_new() && frm.doc.per_paid < 100) {
			frm.add_custom_button(__('Paid'), () => {
				frappe.prompt({
					label: 'Paid Amount',
					fieldname: 'paid_amount',
					fieldtype: 'Currency',
					options: 'Currency:RUB'
				}, (values) => {
					frm.call({
						doc: frm.doc,
						method: 'set_paid',
						args: {
							'paid_amount': values.paid_amount
						},
						default: frm.doc.pending_amount,
						callback: () => {
							frm.reload_doc();
						}
					});
				});
			}).removeClass('btn-default').addClass('btn-primary');
		}

		if (frm.doc.docstatus == 1 && frm.doc.delivery_status != 'Delivered') {
			frm.add_custom_button(__('Delivered'), () => {
				frm.call({
					doc: frm.doc,
					method: 'set_delivered',
					callback: () => {
						frm.reload_doc();
					}
				});
			}).removeClass('btn-default').addClass('btn-primary');
		}
	},

	validate(frm) {
		frm.doc.child_items = [];
	},

	commission(frm) {
		if (frm.doc.edit_commission == 1) {
			apply_commission(frm);
		}
	},
	edit_commission(frm) {
		if (frm.doc.edit_commission == 0) {
			apply_commission(frm);
		}
	},

	discount(frm) {
		calculate_total_amount(frm);
	},

	total_amount(frm) {
		frm.set_value('pending_amount', frm.doc.total_amount - frm.doc.paid_amount);
	},

	items_cost(frm) {
		apply_commission(frm);
	}
});

function calculate_total_amount(frm) {
	frm.set_value('total_amount', frm.doc.items_cost + frm.doc.margin - frm.doc.discount);
}

async function apply_commission(frm) {
	var args = {
		items_cost: frm.doc.items_cost
	};
	if (frm.doc.edit_commission == 1) {
		args.commission = frm.doc.commission;

	}
	await frappe.call({
		method: 'comfort.comfort.doctype.sales_order.sales_order.calculate_commission',
		args: args,
		callback: (r => {
			frm.set_value('commission', r.message.commission);
			frm.set_value('margin', r.message.margin);
			calculate_total_amount(frm);
		})
	});
}



frappe.ui.form.on("Sales Order Item", {
	item_code(frm, cdt, cdn) {
		var doc = frappe.get_doc(cdt, cdn);
		if (doc.item_code) {
			frappe.db.get_value('Item', doc.item_code, ['rate', 'weight']).then(r => {
				frappe.model.set_value(cdt, cdn, 'qty', 1);
				frappe.model.set_value(cdt, cdn, 'rate', r.message.rate);
				frappe.model.set_value(cdt, cdn, 'weight', r.message.weight);
			});
		}
	},

	qty(frm, cdt, cdn) {
		calculate_item_amount(frm, cdt, cdn);
		calculate_item_total_weight(frm, cdt, cdn);
		calculate_total_quantity(frm);
	},

	rate(frm, cdt, cdn) {
		calculate_item_amount(frm, cdt, cdn);
	},

	amount(frm) {
		calculate_items_cost(frm);
	},

	weight(frm, cdt, cdn) {
		calculate_item_total_weight(frm, cdt, cdn);
	},

	total_weight(frm) {
		calculate_total_weight(frm);
	},

	items_remove(frm) {
		recalculate(frm);
	}
});

function calculate_items_cost(frm) {
	var total = frm.doc.items
		.map(d => d.amount ? d.amount : 0)
		.reduce((a, b) => a + b);
	frm.set_value("items_cost", total);
}

function calculate_item_total_weight(frm, cdt, cdn) {
	var doc = frappe.get_doc(cdt, cdn);
	frappe.model.set_value(cdt, cdn, "total_weight", doc.qty * doc.weight);
}

function calculate_total_quantity(frm) {
	var qty = frm.doc.items
		.map(d => d.amount ? d.qty : 0)
		.reduce((a, b) => a + b);
	frm.set_value("total_quantity", qty);
}

function calculate_item_amount(frm, cdt, cdn) {
	var doc = frappe.get_doc(cdt, cdn);
	frappe.model.set_value(cdt, cdn, "amount", doc.qty * doc.rate);
}

function calculate_total_weight(frm) {
	var total = frm.doc.items
		.map(d => d.total_weight ? d.total_weight : 0)
		.reduce((a, b) => a + b);
	frm.set_value("total_weight", total);
}

function recalculate(frm) {
	calculate_items_cost(frm);
	apply_commission(frm);
	calculate_total_quantity(frm);
	calculate_total_weight(frm);
}