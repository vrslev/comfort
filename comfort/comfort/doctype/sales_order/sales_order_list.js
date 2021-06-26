frappe.listview_settings['Sales Order'] = {
	onload(list) {
		var old_func = frappe.utils.guess_colour;
		frappe.utils.guess_colour = (text) => {
			var colors = {
				"In Progress": "orange",
				"Completed": "green",
				"To Purchase": "red",
				"Purchased": "orange",
				"To Deliver": "orange",
				"Delivered": "green"	,
				"Unpaid": "red",
				"Partially Paid": "orange",
				"Paid": "green",
				"Overpaid": "orange"
			};
			if (colors[text]) {
				return colors[text];
			} else {
				return old_func(text);
			}
		};
	}
};
