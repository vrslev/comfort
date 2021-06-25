import frappe


def get_context(context):
    context.items = frappe.db.get_list('Item',
                                       fields=[
                                           'name', 'item_description', 'image', 'route', 'standard_selling_rate'],
                                       ignore_permissions=True)
    return context
