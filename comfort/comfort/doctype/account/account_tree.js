
frappe.treeview_settings["Account"] = {
	get_tree_nodes: 'comfort.comfort.doctype.account.account.get_children',
	add_tree_node: 'comfort.comfort.doctype.account.account.add_node',
	title: __("Chart of Accounts"),
	get_label: node => node.label == __("Account") ? __("Accounts") : node.label,
	fields: [
		{
			fieldtype: 'Data', fieldname: 'account_name', label: __('New Account Name'), reqd: true,
			description: __("Name of new Account. Note: Please don't create accounts for Customers and Suppliers")
		},
		{
			fieldtype: 'Check', fieldname: 'is_group', label: __('Is Group'),
			description: __('Further accounts can be made under Groups, but entries can be made against non-Groups')
		},
		{
			fieldtype: 'Select', fieldname: 'root_type', label: __('Root Type'),
			options: ['Asset', 'Liability', 'Equity', 'Income', 'Expense'].join('\n'),
			depends_on: 'eval:doc.is_group && !doc.parent_account'
		},
		{
			fieldtype: 'Select', fieldname: 'account_type', label: __('Account Type'),
			options: frappe.get_meta("Account").fields.filter(d => d.fieldname == 'account_type')[0].options,
			description: __("Optional. This setting will be used to filter in various transactions.")
		}
	],
	ignore_fields: ["parent_account"]
};