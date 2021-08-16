import os
import re

import frappe
from comfort.hooks import app_name


def get_py_js_files():
    path = frappe.get_app_path(app_name)
    py: list[str] = []
    js: list[str] = []
    for root, dirs, files in os.walk(path):  # type: ignore
        for f in files:
            if f.endswith(".py"):
                py.append(os.path.join(root, f))
            elif f.endswith(".js"):
                js.append(os.path.join(root, f))
    return py, js


def get_pymethods(files: list[str]):
    all_matches: list[str] = []
    re_match_string = re.compile(r".*?\"comfort[\w+.]+\"")
    re_match_method = re.compile(r"\"(comfort[\w+.]+)\"")
    for file in files:
        with open(file) as f:
            matches = re_match_string.findall(f.read())
            for m in matches:
                if "//" not in m:
                    all_matches.append(re_match_method.findall(m)[0])

    return all_matches


def test_dotted_py_methods_in_code():  # TODO: Use builin frappe's whitelist stuff
    py_files, js_files = get_py_js_files()
    methods_in_py, methods_in_js = get_pymethods(py_files), get_pymethods(js_files)

    for method in methods_in_py:
        frappe.get_attr(method)

    for method in methods_in_js:
        func = frappe.get_attr(method)
        try:
            frappe.is_whitelisted(func)
        except frappe.exceptions.PermissionError as e:
            new_exception = e
            args = list(e.args)
            args.append(method)
            new_exception.args = args
            raise new_exception
