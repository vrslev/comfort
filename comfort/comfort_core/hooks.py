from importlib.metadata import distribution
from typing import Any

import frappe
import frappe.defaults
from comfort import get_doc
from comfort.finance.chart_of_accounts import initialize_accounts
from frappe.core.doctype.doctype.doctype import DocType
from frappe.core.doctype.system_settings.system_settings import SystemSettings
from frappe.geo.doctype.currency.currency import Currency
from frappe.modules import make_boilerplate
from frappe.website.doctype.website_settings.website_settings import WebsiteSettings


def load_metadata():
    """Load required metadata from setup.cfg"""
    meta = distribution("comfort").metadata

    app_name: str = meta["Name"]
    app_title: str = app_name.capitalize()
    app_description: str = meta["Summary"]
    app_publisher = f"{meta['Author']} <{meta['Author-email']}>"
    app_version = meta["Version"]

    return app_name, app_title, app_description, app_publisher, app_version


def _set_currency():
    doc = get_doc(Currency, "RUB")
    doc.update({"symbol": "₽", "enabled": True})
    doc.save()
    frappe.db.set_default("currency", "RUB")


def _update_system_settings():  # pragma: no cover
    doc = get_doc(SystemSettings)
    doc.app_name = "Comfort"  # type: ignore
    doc.date_format = "dd.mm.yyyy"  # type: ignore  # Accepted Russian date format
    doc.number_format = "# ###.##"  # type: ignore  # Accepted Russian money format # type: ignore
    doc.session_expiry = (  # type: ignore
        "720:00"  # Sensible session expiry. Default is 6 hours which is too short
    )
    doc.currency_precision = 0  # type: ignore  # Don't deal with cents
    doc.flags.ignore_mandatory = True  # Helps on fresh site
    doc.save()


def _disable_signup():
    doc = get_doc(WebsiteSettings)
    doc.disable_signup = True  # type: ignore  # Don't want strangers
    doc.home_page = "login"
    doc.save()


def after_install():  # pragma: no cover
    initialize_accounts()
    _set_currency()
    after_migrate()


def after_migrate():  # pragma: no cover
    _update_system_settings()
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


def get_global_search_doctypes():
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
        "Ikea Authorization Server Settings",
        "Telegram Settings",
        "Finance Settings",
        "Vk Api Settings",
        "Vk Form Settings",
    ]
    return {
        "Default": [
            {"doctype": doctype, "index": idx}
            for idx, doctype in enumerate(_doctypes_in_global_search)
        ]
    }
