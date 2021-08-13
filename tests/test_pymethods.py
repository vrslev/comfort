import os
import re

import frappe
from comfort.hooks import app_name


def get_py_js_files():
    path = frappe.get_app_path(app_name)
    all_files: list[str] = []
    for root, dirs, files in os.walk(path):  # type: ignore
        all_files.extend(
            os.path.join(root, f)
            for f in files
            if f.endswith(".js") or f.endswith(".py")
        )
    return all_files


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


def test_dotted_py_methods_in_code():
    methods = get_pymethods(get_py_js_files())
    for match in methods:
        frappe.get_attr(match)
