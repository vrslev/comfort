// Copyright (c) 2016, Shariq and contributors
// For license information, please see license.txt
/* eslint-disable */

frappe.query_reports["Balance Sheet"] = {
	"filters": [
		{
			"fieldname":"company",
			"label": __("Company"),
			"fieldtype": "Link",
			"options": "Company",
			"default": frappe.defaults.get_user_default("Company"),
			"reqd": 1
		},
		{
			"fieldname":"filter_based_on",
			"label": __("Filter Based On"),
			"fieldtype": "Select",
			"options": ["Fiscal Year", "Date Range"],
			"default": ["Fiscal Year"],
			"reqd": 1,
			on_change: function() {
				let filter_based_on = frappe.query_report.get_filter_value('filter_based_on');
				frappe.query_report.toggle_filter_display('fiscal_year', filter_based_on === 'Date Range');
				frappe.query_report.toggle_filter_display('from_date', filter_based_on === 'Fiscal Year');
				frappe.query_report.toggle_filter_display('to_date', filter_based_on === 'Fiscal Year');

				frappe.query_report.refresh();
			}
		},
		{
			"fieldname": "fiscal_year",
			"label": __("Fiscal Year"),
			"fieldtype": "Link",
			"options": "Fiscal Year",
			"reqd": 1,
			"default": frappe.defaults.get_user_default("Fiscal Year"),
			"width": "60px"
		},
		{
			"fieldname":"from_date",
			"label": __("From Date"),
			"fieldtype": "Date",
			"default": frappe.datetime.add_months(frappe.datetime.get_today(), -1),
			"hidden": 1,
			"reqd": 1,
			"width": "60px"
		},
		{
			"fieldname":"to_date",
			"label": __("To Date"),
			"fieldtype": "Date",
			"default": frappe.datetime.get_today(),
			"hidden": 1,
			"reqd": 1,
			"width": "60px"
		},
		{
			"fieldname": "chart_type",
			"label": __("Chart_type"),
			"fieldtype": "Select",
			"options": ["Bar Chart", "Line Chart"],
			"default": "Bar Chart"
		}
	],
	"formatter": function(value, row, column, data, default_formatter) {
		if (data && column.fieldname=="account") {
			value = data.account || value;
			column.is_tree = true;
		}

		value = default_formatter(value, row, column, data);

		if (data && !data.parent_account) {
			value = $(`<span>${value}</span>`);

			var $value = $(value).css("font-weight", "bold");
			if (data.warn_if_negative && data[column.fieldname] < 0) {
				$value.addClass("text-danger");
			}

			value = $value.wrap("<p></p>").parent().html();
		}

		return value;
	},
	"tree": true,
	"name_field": "account",
	"parent_field": "parent_account",
	"initial_depth": 3
};
