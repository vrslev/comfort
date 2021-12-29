from __future__ import annotations

import csv
import os
from typing import Any, Generator

import click
import sentry_sdk

import frappe
import frappe.utils.scheduler
from comfort import doc_exists, get_all, get_doc, new_doc
from comfort.comfort_core.doctype.commission_settings.commission_settings import (
    CommissionSettings,
)
from comfort.comfort_core.hooks import after_install
from comfort.entities.doctype.customer.customer import Customer
from comfort.entities.doctype.item.item import Item
from comfort.hooks import app_name
from comfort.transactions.doctype.purchase_order.purchase_order import PurchaseOrder
from comfort.transactions.doctype.sales_order.sales_order import SalesOrder
from frappe.commands import get_site, pass_context
from frappe.core.doctype.doctype.doctype import DocType
from frappe.core.doctype.module_def.module_def import ModuleDef
from frappe.translate import get_full_dict, get_messages_for_app
from frappe.utils.fixtures import sync_fixtures
from frappe.utils.scheduler import enqueue_events, is_scheduler_inactive


def connect(context: Any):
    frappe.init(get_site(context))
    frappe.connect()


def _cleanup():
    modules: Generator[Any, None, None] = (
        m.name for m in get_all(ModuleDef, filters={"app_name": app_name})
    )
    doctypes = get_all(
        DocType, fields=("name", "issingle"), filters={"module": ("in", modules)}
    )
    for doctype in doctypes:
        if doctype.issingle:  # type: ignore
            if "Settings" in doctype.name:  # type: ignore
                continue
            frappe.db.delete("Singles", {"doctype": doctype.name})
        else:
            frappe.db.delete(doctype.name)  # type: ignore

    after_install()
    sync_fixtures(app_name)
    frappe.db.commit()


def _make_customer():
    doc = {
        "name": "Pavel Durov",
        "gender": "Male",
        "vk_url": "https://vk.com/im?sel=1",
        "phone": "89115553535",
        "city": "Moscow",
        "address": "Arbat, 1",
        "doctype": "Customer",
    }
    if not doc_exists(doc["doctype"], doc["name"]):
        Customer(doc).db_insert()


def _make_commission_settings():
    doc = new_doc(CommissionSettings)
    doc.extend(
        "ranges",
        [
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
    )
    doc.insert()


def _make_items():
    # Last item contains all previous items
    items: list[dict[str, Any]] = [
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
            "item_name": "ПАКС, Гардероб, 175x58x236 см, белый",
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
        if not doc_exists(doc["doctype"], doc["item_code"]):  # type: ignore
            Item(doc).insert()


def _make_sales_order():
    doc = new_doc(SalesOrder)
    doc.customer = "Pavel Durov"
    doc.append(
        "items",
        {
            "item_code": "29128569",
            "qty": 1,
            "item_name": "ПАКС, Гардероб, 175x58x236 см, белый",
        },
    )
    doc.extend(
        "services",
        [
            {
                "type": "Delivery to Apartment",
                "rate": 200,
            },
            {
                "type": "Installation",
                "rate": 600,
            },
        ],
    )
    return doc.insert()


def _add_payment(sales_order: SalesOrder):
    sales_order.add_payment(500, cash=False)


def _make_purchase_order(sales_order_name: str | None):
    get_doc(
        PurchaseOrder,
        {
            "sales_orders": [{"sales_order_name": sales_order_name}],
            "items_to_sell": [{"item_code": "50121575", "qty": 3}],
        },
    ).insert()


def _make_docs():
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


@click.command("write-translations")
@click.argument("untranslated_file", type=str, required=False)
@click.argument("lang", default="ru")
@pass_context
def write_translations(context: Any, untranslated_file: str | None, lang: str):
    "Get untranslated strings for language"
    if untranslated_file is None:
        untranslated_file = frappe.get_app_path(app_name, "translations", "ru.csv")
    connect(context)
    messages: list[tuple[str, ...]] = get_messages_for_app(app_name)
    full_dict: dict[Any, Any] = get_full_dict(lang)

    if untranslated := [m[1] for m in messages if m[1] not in full_dict]:
        print(f"{len(untranslated)} of {len(messages)} translations missing")

        with open(untranslated_file, "a+") as f:
            in_file = [m[0] for m in csv.reader(f)]
            to_write = [[m, ""] for m in untranslated if m not in in_file]
            print(f"Writing {len(to_write)} new translations")
            csv.writer(f).writerows(to_write)
    else:
        print("All translated!")


def _patch_scheduler_enqueue_events_for_site():
    if not os.getenv("SENTRY_DSN"):
        return

    def patched_enqueue_events_for_site(site: str):
        try:
            frappe.connect(site=site)
            if is_scheduler_inactive():
                return

            enqueue_events(site=site)

            frappe.logger("scheduler").debug(f"Queued events for site {site}")

        except frappe.db.OperationalError as exc:
            if frappe.db.is_access_denied(exc):
                frappe.logger("scheduler").debug(f"Access denied for site {site}")
            sentry_sdk.capture_exception(exc)

        except Exception as exc:
            sentry_sdk.capture_exception(exc)

        finally:
            frappe.destroy()

    frappe.utils.scheduler.enqueue_events_for_site = patched_enqueue_events_for_site


@click.command("schedule")
def start_scheduler():
    print("custom scheduler started")
    from frappe.utils.scheduler import start_scheduler

    _patch_scheduler_enqueue_events_for_site()
    start_scheduler()


@click.command("worker")
@click.option("--queue", type=str)
@click.option("--quiet", is_flag=True, default=False)
def start_worker(queue: str, quiet: bool = False):
    from frappe.utils.background_jobs import start_worker

    start_worker(queue=queue, quiet=quiet)


commands = [demo, reset, write_translations, start_scheduler, start_worker]
