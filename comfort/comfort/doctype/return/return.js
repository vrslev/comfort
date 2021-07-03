frappe.provide("comfort");

comfort.ReturnController = frappe.ui.form.Controller.extend({
	setup() {
		this.frm.set_query('voucher_type', () => {
			return {
				filters: {
					'name': ['in', ['Sales Order', 'Purchase Order']]
				}
			};
		});

		// this.frm.set_query('voucher_no', () => {
		// 	let statuses = {
		// 		'Sales Order': ['Purchased', 'To Deliver', 'Delivered', 'Cancelled'],
		// 		'Purchase Order': ['To Receive', 'Completed', 'Cancelled'],
		// 	};
		// 	return {
		// 		filters: {
		// 			'status': ['in', statuses[this.frm.doc.voucher_type]]
		// 		}
		// 	};
		// });

		this.frm.set_query('item_code', 'items', () => {
			return {
				query: 'comfort.comfort.doctype.return.return.items_query',
				filters: {
					voucher_type: this.frm.doc.voucher_type,
					voucher_no: this.frm.doc.voucher_no,
					split_combinations: this.frm.doc.split_combinations,
					sales_order_child_items: this.frm.doc.items
						.filter(d => d.reference_doctype == 'Sales Order Child Item')
						.map(d => d.reference_name),
					sales_order_items: this.frm.doc.items
						.filter(d => d.reference_doctype == 'Sales Order Item')
						.map(d => d.reference_name)
				}
			};
		});
	},


	refresh() {
		this.frm.set_df_property('voucher_type', 'only_select', 1);
		this.frm.set_df_property('voucher_no', 'only_select', 1);
		this.setup_add_items_button();
	},

	voucher_type() {
		this.frm.set_value('voucher_no', '');
	},

	split_combinations(doc) {
		var grid = cur_frm.fields_dict.items.grid;
		if (doc.items && doc.items.length > 0) {
			frappe.confirm(__('All current items will be deleted'), () => {
				doc.items = [];
				$(grid.parent).find('.rows').empty();
				grid.grid_rows = [];
				grid.refresh();
			}, () => {
				doc.split_combinations = !doc.split_combinations;
				refresh_field('split_combinations');
			});
		}
	},

	setup_add_items_button() {
		var me = this;
		this.frm.fields_dict.items.grid.grid_buttons.find('.grid-add-row')
			.unbind()
			.on('click', () => {
				get_items();
			});

		async function get_items() {
			var data = null;
			await me.frm.call({
				doc: me.frm.doc,
				method: 'get_items',
				callback: (r) => {
					data = r.message;
				}
			});
			const fields = [
				{
					fieldtype: 'Link',
					fieldname: "item_code",
					options: 'Item',
					in_list_view: 1,
					label: __('Item Code'),
					read_only: 1
				},
				{
					fieldtype: 'Int',
					fieldname: "qty",
					in_list_view: 1,
					label: __('Quantity')
				}
			];
			if (me.frm.doc.voucher_type == 'Purchase Order') {
				fields.push({
					fieldtype: 'Link',
					fieldname: "sales_order",
					options: 'Sales Order',
					in_list_view: 1,
					label: __('Sales Order'),
					read_only: 1
				});
			}

			var dialog = new frappe.ui.Dialog({
				title: __("Choose Items"),
				size: 'large',
				fields: [{
					fieldname: "items",
					fieldtype: "Table",
					label: "Items",
					cannot_add_rows: true,
					reqd: 1,
					data: data,
					fields: fields
				}],
				primary_action: () => {
					let selected = dialog.fields_dict.items.grid.get_selected_children();
					selected = selected.filter(d => d.__checked);
					me.frm.call({
						doc: me.frm.doc,
						method: 'add_items',
						freeze: 1,
						args: {
							items: selected
						},
						callback: () => {
							me.frm.set_df_property('items', 'depends_on');
							me.frm.doc.__unsaved = 1;
							me.frm.refresh();
						}
					});
					dialog.hide();
				},
				primary_action_label: __('Save')
			});

			let grid = dialog.fields_dict.items.grid;
			grid.grid_buttons.hide();
			grid.wrapper.find('[data-fieldname="item_code"]').unbind('click');

			grid.refresh();

			if (data && data.length > 0) {
				dialog.show();
			} else {
				frappe.show_alert(__('No items to return'));
			}
		}
	},

	items_to_supplier(doc) {
		if (doc.items_to_supplier) {
			this.frm.set_value('items_from_clients', true);
		}
	},

});

function toggle_sales_order_column() {
	let show = cur_frm.doc.voucher_type == 'Purchase Order';
	cur_frm.fields_dict.items.grid.set_column_disp('sales_order', show);
	refresh_field('items');
}

function show_confirm_and_delete_items(doc, if_no) {
	var grid = cur_frm.fields_dict.items.grid;
	return new Promise(resolve => {
		if (doc.items && doc.items.length > 0) {
			frappe.confirm(__('All current items will be deleted'), () => {
				doc.items = [];
				$(grid.parent).find('.rows').empty();
				grid.grid_rows = [];
				grid.refresh();
				resolve();
			}, () => {
				if_no();
				resolve();
			});
		} else {
			resolve();
		}
	});
}

$.extend(cur_frm.cscript, new comfort.ReturnController({ frm: cur_frm }));