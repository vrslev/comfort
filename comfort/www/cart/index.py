import frappe


def get_context(context):
    user = frappe.session.user
    si = frappe.db.sql(
        """ SELECT
					name
				FROM
					`tabSales Invoice`
				WHERE
					party=%s and docstatus=0
				ORDER BY 
					modified desc""",
        user,
        as_dict=1,
    )
    if si:
        context.cart = frappe.get_doc("Sales Invoice", si[0].name)
    return context
