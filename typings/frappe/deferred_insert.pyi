"""
This type stub file was generated by pyright.
"""

import frappe

queue_prefix = ...

@frappe.whitelist()
def deferred_insert(doctype, records): ...
def save_to_db(): ...
def insert_record(record, doctype): ...
def get_key_name(key): ...
def get_doctype_name(key): ...
