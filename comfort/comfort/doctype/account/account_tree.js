
frappe.treeview_settings["Account"] = {
	get_tree_nodes: 'accounting.accounting.doctype.account.account.get_children',
	add_tree_node: 'accounting.accounting.doctype.account.account.add_node',
	get_tree_root: false,
	root_label: "Accounts",
	title: __("Chart of Accounts"),
	filters: [
		{
			fieldname: "company",
			label: __("Company"),
			fieldtype:"Link",
			options: "Company",
			reqd: 1,
			default: frappe.defaults.get_user_default("Company")
		}
	],
	fields: [
		{fieldtype:'Data', fieldname:'account_name', label:__('New Account Name'), reqd:true,
			description: __("Name of new Account. Note: Please don't create accounts for Customers and Suppliers")},
		{fieldtype:'Data', fieldname:'account_number', label:__('Account Number'),
			description: __("Number of new Account, it will be included in the account name as a prefix")},
		{fieldtype:'Check', fieldname:'is_group', label:__('Is Group'),
			description: __('Further accounts can be made under Groups, but entries can be made against non-Groups')},
		{fieldtype:'Select', fieldname:'root_type', label:__('Root Type'),
			options: ['Asset', 'Liability', 'Equity', 'Income', 'Expense'].join('\n'),
			depends_on: 'eval:doc.is_group && !doc.parent_account'},
		{fieldtype:'Select', fieldname:'account_type', label:__('Account Type'),
			options: frappe.get_meta("Account").fields.filter(d => d.fieldname=='account_type')[0].options,
			description: __("Optional. This setting will be used to filter in various transactions.")
		}
	],
	ignore_fields:["parent_account"]
}