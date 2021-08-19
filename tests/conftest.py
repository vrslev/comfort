from typing import Any
from unittest.mock import MagicMock

import pytest
from pymysql import OperationalError

import frappe
from comfort.comfort_core.doctype.commission_settings.commission_settings import (
    CommissionSettings,
)
from comfort.entities.doctype.customer.customer import Customer
from comfort.entities.doctype.item.item import Item
from comfort.entities.doctype.item_category.item_category import ItemCategory
from comfort.finance.chart_of_accounts import initialize_accounts
from comfort.finance.doctype.gl_entry.gl_entry import GLEntry
from comfort.finance.doctype.payment.payment import Payment
from comfort.stock.doctype.receipt.receipt import Receipt
from comfort.transactions.doctype.purchase_order.purchase_order import PurchaseOrder
from comfort.transactions.doctype.sales_order.sales_order import SalesOrder
from frappe.database.mariadb.database import MariaDBDatabase

TEST_SITE_NAME = "tests"


@pytest.fixture
def db_instance():
    """Init frappe, connect to database, do nothing on db.commit()"""
    frappe.init(site=TEST_SITE_NAME, sites_path="../../sites")
    frappe.connect()
    frappe.db.commit = MagicMock()
    yield frappe.db
    frappe.destroy()


@pytest.fixture(autouse=True)
def db_transaction(db_instance: MariaDBDatabase):
    """Rollback after db transaction"""
    try:
        db_instance.begin()
    except OperationalError as e:
        pytest.exit(str(e), returncode=1)

    yield db_instance
    db_instance.rollback()


@pytest.fixture
def customer() -> Customer:
    return frappe.get_doc(
        {
            "name": "Pavel Durov",
            "gender": "Male",
            "vk_id": "1",
            "vk_url": "https://vk.com/im?sel=1",
            "phone": "89115553535",
            "doctype": "Customer",
        }
    )


@pytest.fixture
def child_items() -> list[Item]:
    test_data: list[dict[str, Any]] = [
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
    ]

    return [frappe.get_doc(i).insert() for i in test_data]


@pytest.fixture
def item() -> Item:
    return frappe.get_doc(
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
        }
    )


@pytest.fixture
def item_no_children(item: Item):
    item.child_items = []
    return item


@pytest.fixture
def item_category() -> ItemCategory:
    return frappe.get_doc(
        {
            "name": "Столешницы",
            "item_category_name": "Столешницы",
            "url": "https://www.ikea.com/ru/ru/cat/-11844",
            "doctype": "Item Category",
        }
    )


@pytest.fixture
def accounts():
    frappe.db.sql("DELETE FROM tabAccount")
    initialize_accounts()


@pytest.fixture
@pytest.mark.usefixtures("accounts")
def gl_entry(payment_sales: Payment) -> GLEntry:
    payment_sales.db_insert()
    return frappe.get_doc(
        {
            "name": "GLE-2021-00001",
            "owner": "Administrator",
            "account": "Delivery",
            "debit": 0,
            "credit": 300,
            "voucher_type": "Payment",
            "voucher_no": "ebd35a9cc9",
            "doctype": "GL Entry",
        }
    )


@pytest.fixture
def payment_sales(sales_order: SalesOrder) -> Payment:
    sales_order.db_insert()
    return frappe.get_doc(
        {
            "name": "ebd35a9cc9",
            "docstatus": 0,
            "voucher_type": "Sales Order",
            "voucher_no": "SO-2021-0001",
            "amount": 5000,
            "paid_with_cash": False,
            "doctype": "Payment",
        }
    )


@pytest.fixture
def payment_purchase(purchase_order: PurchaseOrder) -> Payment:
    purchase_order.db_insert()
    return frappe.get_doc(
        {
            "name": "ebd35a9cc9",
            "docstatus": 0,
            "voucher_type": "Purchase Order",
            "voucher_no": "Август-1",
            "amount": 5000,
            "paid_with_cash": False,
            "doctype": "Payment",
        }
    )


@pytest.fixture
def receipt_sales(sales_order: SalesOrder) -> Receipt:
    sales_order.db_insert()
    sales_order.db_update_all()
    return frappe.get_doc(
        {
            "doctype": "Receipt",
            "voucher_type": sales_order.doctype,
            "voucher_no": sales_order.name,
        }
    )


@pytest.fixture
def receipt_purchase(purchase_order: PurchaseOrder) -> Receipt:
    purchase_order.db_insert()
    purchase_order.db_update_all()
    return frappe.get_doc(
        {
            "doctype": "Receipt",
            "voucher_type": purchase_order.doctype,
            "voucher_no": purchase_order.name,
        }
    )


@pytest.fixture
def sales_order(
    customer: Customer,
    child_items: list[Item],
    item: Item,
    commission_settings: CommissionSettings,
):
    customer.insert()
    item.insert()
    commission_settings.insert()

    doc: SalesOrder = frappe.get_doc(
        {
            "name": "SO-2021-0001",
            "customer": "Pavel Durov",
            "edit_commission": 0,
            "discount": 0,
            "paid_amount": 0,
            "doctype": "Sales Order",
            "services": [
                {
                    "type": "Delivery to Entrance",
                    "rate": 300,
                },
                {
                    "type": "Installation",
                    "rate": 500,
                },
            ],
        }
    )
    doc.extend(
        "items",
        [
            {"item_code": item.item_code, "qty": 1},
            {"item_code": child_items[0].item_code, "qty": 2},
        ],
    )
    return doc


@pytest.fixture
def purchase_order(sales_order: SalesOrder) -> PurchaseOrder:
    sales_order.set_child_items()
    sales_order.db_insert()
    sales_order.db_update_all()

    return frappe.get_doc(
        {
            "name": "Август-1",
            "docstatus": 0,
            "status": "Draft",
            "doctype": "Purchase Order",
            "delivery_options": [],
            "sales_orders": [
                {
                    "sales_order_name": "SO-2021-0001",
                    "customer": "Pavel Durov",
                    "total": 24660,
                }
            ],
            "items_to_sell": [
                {
                    "item_code": "29128569",
                    "qty": 1,
                }
            ],
        }
    )


@pytest.fixture
def commission_settings() -> CommissionSettings:
    return frappe.get_doc(
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
    )
