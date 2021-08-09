import frappe
from frappe.utils import cint
from frappe.utils.nestedset import NestedSet


class Account(NestedSet):
    nsm_parent_field = "parent_account"


@frappe.whitelist()
def get_children(doctype, parent=None, is_root=False):

    if is_root:
        parent = ""

    fields = ["name as value", "is_group as expandable"]
    filters = [["docstatus", "<", "2"], ['ifnull(`parent_account`, "")', "=", parent]]

    accounts = frappe.get_list(doctype, fields=fields, filters=filters, order_by="name")

    return accounts


@frappe.whitelist()
def add_node():
    from frappe.desk.treeview import make_tree_args

    args = make_tree_args(**frappe.form_dict)

    if cint(args.is_root):
        args.parent_account = None

    frappe.get_doc(args).insert()
