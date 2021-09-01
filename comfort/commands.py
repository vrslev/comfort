from typing import Any

import click

import frappe
from comfort.comfort_core.hooks import after_install
from comfort.hooks import app_name
from comfort.transactions.doctype.sales_order.sales_order import SalesOrder
from frappe.commands import get_site, pass_context
from frappe.utils.fixtures import sync_fixtures


def connect(context: Any):
    frappe.init(get_site(context))
    frappe.connect()


def _cleanup():
    modules = (
        m.name for m in frappe.get_all("Module Def", filters={"app_name": app_name})
    )
    doctypes: list[Any] = frappe.get_all(
        "DocType",
        fields=("name", "issingle"),
        filters={
            "module": ("in", modules),
            "name": ("not in", ("Ikea Settings", "Telegram Settings")),
        },
    )
    for doctype in doctypes:
        if doctype.issingle:
            frappe.db.sql("DELETE FROM tabSingles WHERE doctype=%s", (doctype.name,))
        else:
            frappe.db.sql(f"DELETE FROM `tab{doctype.name}`")  # nosec

    after_install()
    sync_fixtures(app_name)
    frappe.db.commit()


def _make_customer_group():
    doc = {
        "customer_group_name": "Friends",
        "doctype": "Customer Group",
    }
    if not frappe.db.exists(doc):
        frappe.get_doc(doc).insert()


def _make_customer():
    doc = {
        "name": "Pavel Durov",
        "gender": "Male",
        "vk_url": "https://vk.com/im?sel=1",
        "phone": "89115553535",
        "city": "Moscow",
        "address": "Arbat, 1",
        "doctype": "Customer",
        "customer_group": "Friends",
    }
    if not frappe.db.exists(doc["doctype"], doc["name"]):
        frappe.get_doc(doc).insert()


def _make_commission_settings():
    frappe.get_doc(
        {
            "name": "Commission Settings",
            "doctype": "Commission Settings",
            "ranges": [
                {
                    "percentage": 20,
                    "to_amount": 100,
                },
                {
                    "percentage": 15,
                    "to_amount": 200,
                },
                {
                    "percentage": 10,
                    "to_amount": 0,
                },
            ],
        }
    ).insert()


def _make_items():
    # Last item contains all previous items
    items = [
        {
            "item_code": "10014030",
            "item_name": "ПАКС Каркас гардероба, 50x58x236 см, белый",
            "url": "https://www.ikea.com/ru/ru/p/-10014030",
            "rate": 3100,
            "weight": 41.3,
            "doctype": "Item",
            "child_items": [],
        },
        {
            "item_code": "10366598",
            "item_name": "КОМПЛИМЕНТ Штанга платяная, 75 см, белый",
            "url": "https://www.ikea.com/ru/ru/p/-10366598",
            "rate": 250,
            "weight": 0.43,
            "doctype": "Item",
        },
        {
            "item_code": "20277974",
            "item_name": "КОМПЛИМЕНТ Полка, 75x58 см, белый",
            "url": "https://www.ikea.com/ru/ru/p/-20277974",
            "rate": 400,
            "weight": 4.66,
            "doctype": "Item",
        },
        {
            "item_code": "40277973",
            "item_name": "КОМПЛИМЕНТ Полка, 50x58 см, белый",
            "url": "https://www.ikea.com/ru/ru/p/-40277973",
            "rate": 300,
            "weight": 2.98,
            "doctype": "Item",
        },
        {
            "item_code": "40366634",
            "item_name": "КОМПЛИМЕНТ Ящик, 75x58 см, белый",
            "url": "https://www.ikea.com/ru/ru/p/-40366634",
            "rate": 1700,
            "weight": 7.72,
            "doctype": "Item",
        },
        {
            "item_code": "50121575",
            "item_name": "ПАКС Каркас гардероба, 75x58x236 см, белый",
            "url": "https://www.ikea.com/ru/ru/p/-50121575",
            "rate": 3600,
            "weight": 46.8,
            "doctype": "Item",
        },
        {
            "item_code": "50366596",
            "item_name": "КОМПЛИМЕНТ Штанга платяная, 50 см, белый",
            "url": "https://www.ikea.com/ru/ru/p/-50366596",
            "rate": 200,
            "weight": 0.3,
            "doctype": "Item",
        },
        {
            "item_code": "29128569",
            "item_name": "ПАКС Гардероб, 175x58x236 см, белый",
            "url": "https://www.ikea.com/ru/ru/p/-s29128569",
            "rate": 17950,
            "doctype": "Item",
            "child_items": [
                {
                    "item_code": "10014030",
                    "item_name": "ПАКС Каркас гардероба, 50x58x236 см, белый",
                    "qty": 2,
                },
                {
                    "item_code": "10366598",
                    "item_name": "КОМПЛИМЕНТ Штанга платяная, 75 см, белый",
                    "qty": 1,
                },
                {
                    "item_code": "20277974",
                    "item_name": "КОМПЛИМЕНТ Полка, 75x58 см, белый",
                    "qty": 2,
                },
                {
                    "item_code": "40277973",
                    "item_name": "КОМПЛИМЕНТ Полка, 50x58 см, белый",
                    "qty": 6,
                },
                {
                    "item_code": "40366634",
                    "item_name": "КОМПЛИМЕНТ Ящик, 75x58 см, белый",
                    "qty": 3,
                },
                {
                    "item_code": "50121575",
                    "item_name": "ПАКС Каркас гардероба, 75x58x236 см, белый",
                    "qty": 1,
                },
                {
                    "item_code": "50366596",
                    "item_name": "КОМПЛИМЕНТ Штанга платяная, 50 см, белый",
                    "qty": 1,
                },
            ],
        },
    ]
    for doc in items:
        if not frappe.db.exists(doc["doctype"], doc["item_code"]):
            frappe.get_doc(doc).insert()


def _make_sales_order():
    doc: SalesOrder = frappe.get_doc(
        {
            "customer": "Pavel Durov",
            "doctype": "Sales Order",
            "items": [
                {
                    "item_code": "29128569",
                    "qty": 1,
                    "item_name": "ПАКС Гардероб, 175x58x236 см, белый",
                }
            ],
            "services": [
                {
                    "type": "Delivery to Apartment",
                    "rate": 200,
                },
                {
                    "type": "Installation",
                    "rate": 600,
                },
            ],
        }
    )
    doc.insert()
    return doc


def _add_payment(sales_order: SalesOrder):
    sales_order.add_payment(500, cash=False)


def _make_purchase_order(sales_order_name: str):
    frappe.get_doc(
        {
            "doctype": "Purchase Order",
            "sales_orders": [{"sales_order_name": sales_order_name}],
            "items_to_sell": [{"item_code": "50121575", "qty": 3}],
        }
    ).insert()


def _make_docs():
    _make_customer_group()
    _make_customer()
    _make_items()
    _make_commission_settings()
    sales_order = _make_sales_order()
    _add_payment(sales_order)
    _make_purchase_order(sales_order.name)
    frappe.db.commit()


@click.command("demo")
@click.option("--clean", is_flag=True)
@pass_context
def demo(context: Any, clean: bool):
    connect(context)
    if clean:
        _cleanup()
    _make_docs()


@click.command("reset")
@pass_context
def reset(context: Any):
    connect(context)
    _cleanup()


commands = [demo, reset]
