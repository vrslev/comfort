"""
This type stub file was generated by pyright.
"""

import frappe

class ServerScriptNotEnabled(frappe.PermissionError): ...

class NamespaceDict(frappe._dict):
    """Raise AttributeError if function not found in namespace"""

    def __getattr__(self, key): ...

def safe_exec(script, _globals=..., _locals=...): ...
def get_safe_globals(): ...
def read_sql(query, *args, **kwargs):
    """a wrapper for frappe.db.sql to allow reads"""
    ...

def run_script(script):
    """run another server script"""
    ...

def add_data_utils(data): ...
def add_module_properties(module, data, filter_method): ...

VALID_UTILS = ...
