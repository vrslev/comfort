frappe.listview_settings['Sales Order'] = {
	onload(list) {
		var old_func = frappe.utils.guess_colour;
		frappe.utils.guess_colour = (text) => {
			var colors = {
				"In Progress": "orange",
				"Completed": "green",
				"To Purchase": "orange",
				"Purchased": "orange",
				"To Deliver": "orange",
				"Delivered": "green"
			};
			if (colors[text]) {
				return colors[text];
			} else {
				return old_func(text);
			}
		};
	}
};
