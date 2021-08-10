from __future__ import annotations

from typing import Any

import frappe


def extend_boot_session_with_currency(bootinfo: object):
    # TODO: Currency symbol not working
    bootinfo.sysdefaults.currency = frappe.get_cached_value(
        "Accounts Settings", "Accounts Settings", "default_currency"
    )

    bootinfo.sysdefaults.currency_precision = 0

    if bootinfo.sysdefaults.currency:
        currency_doc: dict[str, Any] = frappe.get_cached_value(
            "Currency",
            bootinfo.sysdefaults.currency,
            [
                "name",
                "fraction",
                "fraction_units",
                "number_format",
                "smallest_currency_fraction_value",
                "symbol",
            ],
            as_dict=True,
        )
        currency_doc["doctype"] = ":Currency"
        bootinfo.docs.append(currency_doc)
