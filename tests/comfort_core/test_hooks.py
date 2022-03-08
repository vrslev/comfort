import frappe
from comfort.comfort_core.hooks import _disable_signup, _set_currency, load_metadata
from comfort.utils import get_doc, get_value
from frappe.geo.doctype.currency.currency import Currency


def test_load_metadata():
    for value in load_metadata():
        assert isinstance(value, str)


def test_set_currency():
    _set_currency()
    doc = get_doc(Currency, "RUB")
    assert doc.symbol == "₽"  # type: ignore
    assert doc.enabled  # type: ignore
    assert frappe.db.get_default("currency") == "RUB"


def test_disable_signup():
    frappe.db.set_value("Website Settings", None, "disable_signup", 0)
    _disable_signup()
    assert int(get_value("Website Settings", None, "disable_signup")) == 1
