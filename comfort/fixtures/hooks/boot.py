import frappe


def boot_session(bootinfo):
    bootinfo.sysdefaults.currency = frappe.get_cached_value(
        "Accounts Settings", "Accounts Settings", "default_currency"
    )
    bootinfo.sysdefaults.currency_precision = 0
    if bootinfo.sysdefaults.currency:
        val = frappe.get_cached_value(
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
        val["doctype"] = ":Currency"
        bootinfo.docs.append(val)
