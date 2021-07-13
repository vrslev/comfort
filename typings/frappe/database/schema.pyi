"""
This type stub file was generated by pyright.
"""

import frappe

class InvalidColumnName(frappe.ValidationError): ...

class DBTable:
    def __init__(self, doctype, meta=...) -> None: ...
    def sync(self): ...
    def create(self): ...
    def get_column_definitions(self): ...
    def get_index_definitions(self): ...
    def get_columns_from_docfields(self):  # -> None:
        """
        get columns from docfields and custom fields
        """
        ...
    def validate(self):  # -> None:
        """Check if change in varchar length isn't truncating the columns"""
        ...
    def is_new(self): ...
    def setup_table_columns(self): ...
    def alter(self): ...

class DbColumn:
    def __init__(
        self,
        table,
        fieldname,
        fieldtype,
        length,
        default,
        set_index,
        options,
        unique,
        precision,
    ) -> None: ...
    def get_definition(self, with_default=...): ...
    def build_for_alter_table(self, current_def): ...
    def default_changed(self, current_def): ...
    def default_changed_for_decimal(self, current_def): ...

def validate_column_name(n): ...
def validate_column_length(fieldname): ...
def get_definition(fieldtype, precision=..., length=...): ...
def add_column(doctype, column_name, fieldtype, precision=...): ...
