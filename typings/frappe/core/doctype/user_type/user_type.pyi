"""
This type stub file was generated by pyright.
"""

import frappe
from frappe.model.document import Document

class UserType(Document):
    def validate(self): ...
    def on_update(self): ...
    def on_trash(self): ...
    def set_modules(self): ...
    def validate_document_type_limit(self): ...
    def validate_role(self): ...
    def update_users(self): ...
    def update_roles_in_user(self, user): ...
    def update_modules_in_user(self, user): ...
    def add_role_permissions_for_user_doctypes(self): ...
    def add_select_perm_doctypes(self): ...
    def prepare_select_perm_doctypes(self, doc, user_doctypes, select_doctypes): ...
    def add_role_permissions_for_select_doctypes(self): ...
    def add_role_permissions_for_file(self): ...
    def remove_permission_for_deleted_doctypes(self): ...

def add_role_permissions(doctype, role): ...
def get_non_standard_user_type_details(): ...
@frappe.whitelist()
@frappe.validate_and_sanitize_search_inputs
def get_user_linked_doctypes(doctype, txt, searchfield, start, page_len, filters): ...
@frappe.whitelist()
def get_user_id(parent): ...
def user_linked_with_permission_on_doctype(doc, user): ...
def apply_permissions_for_non_standard_user_type(doc, method=...):  # -> None:
    """Create user permission for the non standard user type"""
    ...
