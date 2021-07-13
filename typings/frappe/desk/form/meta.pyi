"""
This type stub file was generated by pyright.
"""

from frappe.model.meta import Meta

def get_meta(doctype, cached=...): ...

class FormMeta(Meta):
    def __init__(self, doctype) -> None: ...
    def load_assets(self): ...
    def as_dict(self, no_nulls=...): ...
    def add_code(self): ...
    def add_html_templates(self, path): ...
    def add_code_via_hook(self, hook, fieldname): ...
    def add_custom_script(self):  # -> None:
        """embed all require files"""
        ...
    def add_search_fields(self):  # -> None:
        """add search fields found in the doctypes indicated by link fields' options"""
        ...
    def add_linked_document_type(self): ...
    def load_print_formats(self): ...
    def load_workflows(self): ...
    def load_templates(self): ...
    def set_translations(self, lang): ...
    def load_dashboard(self): ...
    def load_kanban_meta(self): ...
    def load_kanban_column_fields(self): ...

def get_code_files_via_hooks(hook, name): ...
def get_js(path): ...
