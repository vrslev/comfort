import os

import frappe
from frappe.translate import get_translation_dict_from_file


def get_translated_dict() -> dict[str, str]:
    if frappe.lang == "ru":
        path = os.path.join(os.path.dirname(__file__), "ru.csv")
        return get_translation_dict_from_file(path, "ru", "comfort")
    return {}
