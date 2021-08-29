import frappe
from comfort.comfort_core.hooks import (
    _add_app_name,
    _set_currency_symbol,
    _set_default_date_and_number_format,
    load_metadata,
)
from frappe.geo.doctype.currency.currency import Currency


def test_load_metadata():
    for value in load_metadata():
        assert isinstance(value, str)


def test_set_currency_symbol():
    _set_currency_symbol()
    doc: Currency = frappe.get_doc("Currency", "RUB")
    assert doc.symbol == "₽"
    assert doc.enabled
    assert frappe.db.get_default("currency") == "RUB"
    assert int(frappe.db.get_default("currency_precision")) == 0


def test_add_app_name():
    _add_app_name()
    assert frappe.db.get_value("System Settings", None, "app_name") == "Comfort"


def test_set_default_date_and_number_format():
    _set_default_date_and_number_format()
    date_format = "dd.mm.yyyy"
    assert frappe.db.get_default("date_format") == date_format
    assert frappe.db.get_value("System Settings", None, "date_format") == date_format
    assert frappe.db.get_value("System Settings", None, "number_format") == "#.###,##"


# TODO: Cover comfort.comfort_core.hooks.get_standard_queries

# TODO: Cover hooks presence
# -after_install = "comfort.comfort_core.hooks.after_install"
# +after_install = None

# TODO: Cover doctype override
# -override_doctype_class = {"DocType": "comfort.comfort_core.hooks.CustomDocType"}
# +override_doctype_class = {"XXDocTypeXX": "comfort.comfort_core.hooks.CustomDocType"}

# TODO: Cover treeviews
# -treeviews = ["Account"]
# +treeviews = ["XXAccountXX"]
