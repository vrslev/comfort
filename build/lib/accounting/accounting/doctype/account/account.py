

from frappe.utils.nestedset import NestedSet

class Account(NestedSet):
    nsm_parent_field = "parent_account"