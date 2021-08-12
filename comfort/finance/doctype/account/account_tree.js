frappe.treeview_settings["Account"] = {
  get_tree_nodes: "comfort.finance.doctype.account.account.get_children",
  add_tree_node: "comfort.finance.doctype.account.account.add_node",
  title: __("Chart of Accounts"),
  get_label: (node) =>
    node.label == __("Account") ? __("Accounts") : node.label,
  fields: [
    {
      fieldtype: "Data",
      fieldname: "account_name",
      label: __("New Account Name"),
      reqd: true,
      description: __(
        "Name of new Account. Note: Please don't create accounts for Customers and Suppliers"
      ),
    },
    {
      fieldtype: "Check",
      fieldname: "is_group",
      label: __("Is Group"),
      description: __(
        "Further accounts can be made under Groups, but entries can be made against non-Groups"
      ),
    },
    {
      fieldtype: "Select",
      fieldname: "root_type",
      label: __("Root Type"),
      options: ["Asset", "Liability", "Equity", "Income", "Expense"].join("\n"),
      depends_on: "eval:doc.is_group && !doc.parent_account",
    },
  ],
  ignore_fields: ["parent_account"],
};
