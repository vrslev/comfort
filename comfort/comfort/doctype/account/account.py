import frappe
from frappe.utils import cint
from frappe.utils.nestedset import NestedSet


class Account(NestedSet):
    nsm_parent_field = "parent_account"

    def after_insert(self):
        if self.account_type == 'Bank':
            company = frappe.get_doc('Company', self.company)
            if not company.default_bank_account:
                company.db_set('default_bank_account', self.account_name)


@frappe.whitelist()
def get_children(doctype, parent=None, company=None, is_root=False):

    if is_root:
        parent = ""

    fields = ['name as value', 'is_group as expandable']
    filters = [
        ['docstatus', '<', '2'],
        ['ifnull(`parent_account`, "")', '=', parent],
        ['company', 'in', (company, None, '')]
    ]

    accounts = frappe.get_list(
        doctype, fields=fields, filters=filters, order_by='name')

    return accounts


@frappe.whitelist()
def add_node():
    from frappe.desk.treeview import make_tree_args
    args = make_tree_args(**frappe.form_dict)

    if cint(args.is_root):
        args.parent_account = None

    frappe.get_doc(args).insert()


@frappe.whitelist()
def get_company():
    company = []
    for d in frappe.db.sql("""SELECT
						name
					FROM
						tabCompany"""):
        company.append(d[0])
    return company
