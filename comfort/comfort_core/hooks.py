from __future__ import annotations

from configparser import ConfigParser
from pathlib import Path
from typing import Any, Callable, Iterable

import frappe
import frappe.defaults
from comfort.finance.chart_of_accounts import initialize_accounts
from frappe.core.doctype.doctype.doctype import DocType
from frappe.desk.reportview import get_filters_cond, get_match_cond
from frappe.geo.doctype.currency.currency import Currency
from frappe.model.meta import Meta
from frappe.modules import make_boilerplate
from frappe.utils import unique


def load_metadata():
    """Load required metadata from setup.cfg"""
    path = Path(__file__).parent.parent.parent.joinpath("setup.cfg")
    config = ConfigParser()
    config.read(path)

    meta = config["metadata"]
    app_name, app_description = meta["name"], meta["description"]
    app_title = app_name.capitalize()
    app_publisher = f"{meta['author']} <{meta['author_email']}>"

    return app_name, app_title, app_description, app_publisher


def _format_money(money: str | int):  # pragma: no cover
    return f"{int(money)} ₽"


def _format_weight(weight: int | float):  # pragma: no cover
    return f"{float(weight)} кг"


def _format_item_query(d: list[Any]):  # pragma: no cover
    if d[2]:
        d[2] = _format_money(d[2])


def _format_purchase_order_query(d: list[Any]):  # pragma: no cover
    if d[2]:
        d[2] = _format_money(d[2])
    if d[3]:
        d[3] = _format_weight(d[3])


def _format_sales_order_query(d: list[Any]):  # pragma: no cover
    if d[3]:
        d[3] = _format_money(d[3])


_QUERY_FORMATTERS: dict[str, Callable[[list[Any]], Any]] = {  # pragma: no cover
    "Item": _format_item_query,
    "Purchase Order": _format_purchase_order_query,
    "Sales Order": _format_sales_order_query,
}


def _get_fields(
    doctype: str, fields: list[Any] | None = None
) -> list[Any]:  # pragma: no cover
    # From ERPNext
    if fields is None:
        fields = []
    meta: Meta = frappe.get_meta(doctype)
    search_fields: list[Any] = meta.get_search_fields()
    fields.extend(search_fields)

    title_field: str | None = meta.get("title_field")  # type: ignore
    if title_field and not title_field.strip() in fields:
        fields.insert(1, title_field.strip())

    return unique(fields)


@frappe.whitelist()  # pragma: no cover
@frappe.validate_and_sanitize_search_inputs
def default_query(
    doctype: str,
    txt: str,
    searchfield: str,
    start: int,
    page_len: int,
    filters: dict[Any, Any],
):
    conditions = []
    fields = _get_fields(doctype, ["name"])

    query: list[tuple[Any]] = frappe.db.sql(
        f"""
        SELECT {", ".join(fields)} FROM `tab{doctype}`
        WHERE {searchfield} LIKE %(txt)s
        {get_filters_cond(doctype, filters, conditions)}
        {get_match_cond(doctype)}

        ORDER BY modified DESC
        LIMIT {start}, {page_len}
        """,
        {"txt": "%%%s%%" % txt},
        as_list=True,
    )
    if doctype in _QUERY_FORMATTERS:
        for d in query:
            _QUERY_FORMATTERS[doctype](d)
    return query


def get_standard_queries(doctypes: Iterable[str]):  # pragma: no cover
    query_name = default_query.__module__ + "." + default_query.__name__
    return {d: query_name for d in doctypes}


def _create_comfort_user_role():
    doc = {"doctype": "Role", "name": "Comfort User"}
    if frappe.db.exists(doc):
        frappe.delete_doc(doc["doctype"], doc["name"])
    else:
        frappe.get_doc(
            {
                **doc,
                "doctype": "Role",
                "name": "Comfort User",
                "role_name": "Comfort User",
                "desk_access": 1,
                "two_factor_auth": 0,
                "search_bar": 1,
                "notifications": 0,
                "chat": 0,
                "list_sidebar": 1,
                "bulk_actions": 1,
                "view_switcher": 0,  # List/Report/Kanban views
                "form_sidebar": 1,
                "timeline": 1,
                "dashboard": 1,
                "is_custom": 0,
            }
        ).insert()


def before_install():
    _create_comfort_user_role()
    frappe.db.commit()


def _set_currency_symbol():
    doc: Currency = frappe.get_doc("Currency", "RUB")
    doc.symbol = "₽"
    doc.enabled = True
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


def after_install():  # pragma: no cover
    initialize_accounts()
    _set_currency_symbol()
    _add_app_name()
    _set_default_date_and_number_format()


def extend_boot_session(bootinfo: Any):  # pragma: no cover
    currency_doc: dict[str, Any] = frappe.get_cached_value(
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
