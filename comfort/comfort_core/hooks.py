from importlib.metadata import distribution
from typing import Any

import frappe
import frappe.defaults
from comfort.finance.chart_of_accounts import initialize_accounts
from frappe.core.doctype.doctype.doctype import DocType
from frappe.geo.doctype.currency.currency import Currency
from frappe.modules import make_boilerplate


def load_metadata():
    """Load required metadata from setup.cfg"""
    meta = distribution("comfort").metadata

    app_name: str = meta["Name"]
    app_title: str = app_name.capitalize()
    app_description: str = meta["Summary"]
    app_publisher = f"{meta['Author']} <{meta['Author-email']}>"
    app_version = meta["Version"]

    return app_name, app_title, app_description, app_publisher, app_version


def _set_currency_symbol():
    doc: Currency = frappe.get_doc("Currency", "RUB")  # type: ignore
    doc.update({"symbol": "₽", "enabled": True})
    doc.save()
    frappe.db.set_default("currency", "RUB")
    frappe.db.set_default("currency_precision", 0)


def _add_app_name():  # TODO: Make normal tests (insert another value before testing this)
    frappe.db.set_value("System Settings", None, "app_name", "Comfort")


def _set_default_date_and_number_format():
    date_format = "dd.mm.yyyy"
    frappe.db.set_default("date_format", date_format)
    frappe.db.set_value("System Settings", None, "date_format", date_format)
    frappe.db.set_value("System Settings", None, "number_format", "#.###,##")


def _disable_signup():
    frappe.db.set_value("Website Settings", None, "disable_signup", 1)


def after_install():  # pragma: no cover
    initialize_accounts()
    _set_currency_symbol()
    _add_app_name()
    _set_default_date_and_number_format()
    _disable_signup()


def extend_boot_session(bootinfo: Any):  # pragma: no cover
    currency_doc: dict[str, Any] = frappe.get_cached_value(  # type: ignore
        "Currency",
        bootinfo.sysdefaults.currency,
        (
            "name",
            "fraction",
            "fraction_units",
            "number_format",
            "smallest_currency_fraction_value",
            "symbol",
        ),
        as_dict=True,
    )
    currency_doc["doctype"] = ":Currency"
    bootinfo.docs.append(currency_doc)


class CustomDocType(DocType):  # pragma: no cover
    def make_controller_template(self):
        """Do not madly create dt.js, test_dt.py files"""
        make_boilerplate("controller._py", self)


def get_global_search_doctypes():  # pragma: no cover
    _doctypes_in_global_search = [
        #
        # Major doctypes
        #
        "Sales Order",
        "Purchase Order",
        "Sales Return",
        "Purchase Return",
        "Delivery Trip",
        #
        # Semi major doctypes
        #
        "Payment",
        "Checkout",
        "Receipt",
        #
        # Various entities
        #
        "Customer",
        "Item",
        "Account",
        "Customer Group",
        "Item Category",
        # "GL Entry",
        # "Stock Entry",
        #
        # Settings
        #
        "Commission Settings",
        "Ikea Settings",
        "Telegram Settings",
        "Finance Settings",
        "Vk Form Settings",
    ]
    return {
        "Default": [
            {"doctype": doctype, "index": idx}
            for idx, doctype in enumerate(_doctypes_in_global_search)
        ]
    }
