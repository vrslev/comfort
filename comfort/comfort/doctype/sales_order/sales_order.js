frappe.ui.form.on('Sales Order', {
	setup(frm) {
		frm.page.sidebar.hide();
	},

	onload_post_render(frm) {
		frm.fields_dict.items.$wrapper
			.unbind('paste')
			.on('paste', e => {
				e.preventDefault();
				let clipboard_data = e.clipboardData || window.clipboardData || e.originalEvent.clipboardData;
				let pasted_data = clipboard_data.getData('Text');
				if (!pasted_data) return;

				quick_add_items(pasted_data);
			});
		return false;
	},

	refresh(frm) {
		if (!frm.is_new() && frm.doc.per_paid < 100) {
			frm.add_custom_button(__('Paid'), () => {
				frappe.prompt([{
					label: 'Paid Amount',
					fieldname: 'paid_amount',
					fieldtype: 'Currency',
					precision: "0",
					default: frm.doc.pending_amount,
				},
				{
					label: 'Account',
					fieldname: 'account',
					fieldtype: 'Select',
					options: 'Cash\nBank'
				}], (values) => {
					frm.call({
						doc: frm.doc,
						method: 'set_paid',
						args: {
							paid_amount: values.paid_amount,
							cash: values.account == 'Cash'
						},
						callback: () => {
							frm.reload_doc();
						}
					});
				});
			}).removeClass('btn-default').addClass('btn-primary');
		}

		if (frm.doc.delivery_status == 'To Deliver') {
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

		if (frm.doc.docstatus == 0 && frm.doc.child_items && frm.doc.child_items.length > 0) {
			frm.add_custom_button(__('Split Combinations'), () => {
				const fields = [{
					fieldtype: 'Link',
					fieldname: "item_code",
					options: 'Item',
					in_list_view: 1,
					label: __('Item Code')
				}];

				var dialog = new frappe.ui.Dialog({
					title: __("Split Combinations"),
					fields: [{
						fieldname: "combinations",
						fieldtype: "Table",
						label: "Combinations",
						cannot_add_rows: true,
						size: 'large',
						reqd: 1,
						data: [],
						fields: fields
					}],
					primary_action: () => {
						let selected = dialog.fields_dict.combinations.grid.get_selected_children();
						selected = selected.filter(d => d.__checked);
						selected = selected.map(d => d.item_code);
						frm.call({
							doc: frm.doc,
							method: 'split_combinations',
							freeze: 1,
							args: {
								combos_to_split: selected,
								save: true
							}
						});
						dialog.hide();
					},
					primary_action_label: __('Save')
				});

				var parent_items = [];
				frm.doc.child_items.forEach(d => {
					parent_items.push(d.parent_item_code);
				});
				frm.doc.items.forEach(d => {
					if (parent_items.includes(d.item_code)) {
						dialog.fields_dict.combinations.df.data.push({
							"name": d.name,
							"item_code": d.item_code,
							"item_name": d.item_name
						});
					}
				});
				dialog.fields_dict.combinations.grid.refresh();
				if (!frm.doc.child_items || frm.doc.child_items.length == 0 || dialog.fields_dict.combinations.grid.data.length == 0) {
					frappe.msgprint('В заказе нет комбинаций');
					return;
				}

				dialog.fields_dict.combinations.grid.display_status = 'Read';
				dialog.fields_dict.combinations.grid.grid_buttons.hide();
				dialog.show();
			});
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
			frappe.db.get_value('Item', doc.item_code, ['item_name', 'rate', 'weight']).then(r => {
				frappe.model.set_value(cdt, cdn, 'qty', 1);
				frappe.model.set_value(cdt, cdn, 'item_name', r.message.item_name);
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
	calculate_total_quantity(frm);
	calculate_total_weight(frm);
}


async function quick_add_items(text) {
	comfort.fetch_items(text).then(r => {
		let promises = [];
		function callback(d) {
			return frappe.db.get_value('Item', d, ['item_name', 'rate', 'weight']).then(r => {
				let doc = cur_frm.add_child('items', {
					item_code: d,
					qty: 1,
					item_name: r.message.item_name,
					rate: r.message.rate,
					weight: r.message.weight
				});
				let cdt = doc.doctype;
				let cdn = doc.name;

				calculate_item_amount(cur_frm, cdt, cdn);
				calculate_item_total_weight(cur_frm, cdt, cdn);
			});
		}

		for (var d of r.successful) {
			promises.push(callback(d));
		}

		return Promise.all(promises).then(() => {
			recalculate(cur_frm);

			let grid = cur_frm.fields_dict.items.grid;

			// loose focus from current row
			grid.add_new_row(null, null, true);
			grid.grid_rows[grid.grid_rows.length - 1].toggle_editable_row();

			let grid_rows = grid.grid_rows;
			for (var i = grid_rows.length; i--;) {
				let doc = grid_rows[i].doc;
				if (!(doc.item_name && doc.item_code)) {
					grid_rows[i].remove();
				}
			}

			refresh_field('items');
		});
	});
}