import re

import frappe
from ikea_api_extender import unshorten_ingka_pagelinks


def extract_item_codes(message):
    item_codes_raw = re.findall(
        r'\d{3}[, .-]{0,2}\d{3}[, .-]{0,2}\d{2}', message)
    regex = re.compile(r'[^0-9]')
    try:
        res = [re.sub(regex, '', i) for i in item_codes_raw]
        return list(set(res))
    except TypeError:
        return []


def format_item_code(item_code):
    found = extract_item_codes(item_code)
    if len(found) > 0:
        item_code = found[0]
    return item_code[0:3] + '.' + item_code[3:6] + '.' + item_code[6:8]


@frappe.whitelist()
def get_item_codes_from_ingka_pagelinks(text):
    unshortened = unshorten_ingka_pagelinks(text)
    item_codes = extract_item_codes(unshortened)
    return item_codes
