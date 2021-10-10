frappe.treeview_settings["Account"] = {
  title: __("Chart of Accounts"),
  root_label: "Accounts",
  get_tree_nodes: "comfort.finance.doctype.account.account.get_children",
  add_tree_node: "comfort.finance.doctype.account.account.add_node",
  fields: [
    {
      fieldtype: "Data",
      fieldname: "account_name",
      label: __("New Account name"),
      reqd: true,
    },
    {
      fieldtype: "Check",
      fieldname: "is_group",
      label: __("Is Group"),
    },
  ],
  ignore_fields: ["parent_account"],
  get_label: (node) =>
    node.label == __("Account") ? __("Accounts") : __(node.label),
  onrender: (node) => {
    if (node.data && node.data.balance !== undefined) {
      $(
        '<span class="balance-area pull-right">' +
          format_currency(node.data.balance) +
          "</span>"
      ).insertBefore(node.$ul);
    }
  },
};
