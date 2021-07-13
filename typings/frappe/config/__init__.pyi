"""
This type stub file was generated by pyright.
"""

from __future__ import unicode_literals

import json

from six import iteritems

import frappe
from frappe import _
from frappe.desk.moduleview import (
    config_exists,
    get_data,
    get_module_link_items_from_list,
    get_onboard_items,
)

def get_modules_from_all_apps_for_user(user=...): ...
def get_modules_from_all_apps(): ...
def get_modules_from_app(app): ...
def get_all_empty_tables_by_module(): ...
def is_domain(module): ...
def is_module(module): ...
