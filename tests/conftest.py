from datetime import date
from types import SimpleNamespace
from typing import Any, Callable
from unittest.mock import MagicMock

import ikea_api.auth
import ikea_api_wrapped
import pytest
from ikea_api_wrapped.types import (
    DeliveryOptionDict,
    GetDeliveryServicesResponse,
    ParsedItem,
    PurchaseInfoDict,
    UnavailableItemDict,
)
from pymysql import OperationalError

import frappe
from comfort import TypedDocument, doc_exists, get_doc
from comfort.comfort_core.doctype.commission_settings.commission_settings import (
    CommissionSettings,
)
from comfort.comfort_core.doctype.ikea_settings.ikea_settings import IkeaSettings
from comfort.comfort_core.doctype.telegram_settings.telegram_settings import (
    TelegramSettings,
)
from comfort.entities.doctype.customer.customer import Customer
from comfort.entities.doctype.item.item import Item
from comfort.entities.doctype.item_category.item_category import ItemCategory
from comfort.finance.chart_of_accounts import initialize_accounts
from comfort.finance.doctype.gl_entry.gl_entry import GLEntry
from comfort.finance.doctype.payment.payment import Payment
from comfort.stock.doctype.checkout.checkout import Checkout
from comfort.stock.doctype.delivery_trip.delivery_trip import DeliveryTrip
from comfort.stock.doctype.receipt.receipt import Receipt
from comfort.transactions.doctype.purchase_order.purchase_order import PurchaseOrder
from comfort.transactions.doctype.purchase_return.purchase_return import PurchaseReturn
from comfort.transactions.doctype.sales_order.sales_order import SalesOrder
from comfort.transactions.doctype.sales_return.sales_return import SalesReturn
from frappe.database.mariadb.database import MariaDBDatabase

TEST_SITE_NAME = "tests"
# TODO: Better way to get hard coded doc names. E.g: "SO-2021-0001" valid only in 2021


def patch_frappe_document():
    import frappe.model.document

    def save_version(self: frappe.model.document.Document):
        return

    frappe.model.document.Document.save_version = save_version


@pytest.fixture(scope="session")
def db_instance():
    """Init frappe, connect to database, do nothing on db.commit()"""
    frappe.init(site=TEST_SITE_NAME, sites_path="../../sites")
    frappe.flags.in_test = True
    frappe.local.dev_server = True
    frappe.connect()
    frappe.db.commit = MagicMock()
    patch_frappe_document()

    yield frappe.db
    frappe.db.close()


@pytest.fixture(autouse=True)
def db_transaction(db_instance: MariaDBDatabase):
    """Rollback after db transaction"""
    try:
        yield db_instance
    except OperationalError as e:
        pytest.exit(str(e), returncode=1)
    db_instance.rollback()


@pytest.fixture
def customer():
    return get_doc(
        Customer,
        {
            "name": "Pavel Durov",
            "gender": "Male",
            "vk_id": "1",
            "vk_url": "https://vk.com/im?sel=1",
            "phone": "89115553535",
            "city": "Moscow",
            "address": "Arbat, 1",
        },
    )


@pytest.fixture
def child_items():
    test_data: list[dict[str, Any]] = [
        {
            "item_code": "10014030",
            "item_name": "ПАКС Каркас гардероба, 50x58x236 см, белый",
            "url": "https://www.ikea.com/ru/ru/p/-10014030",
            "rate": 3100,
            "weight": 41.3,
            "child_items": [],
        },
        {
            "item_code": "10366598",
            "item_name": "КОМПЛИМЕНТ Штанга платяная, 75 см, белый",
            "url": "https://www.ikea.com/ru/ru/p/-10366598",
            "rate": 250,
            "weight": 0.43,
        },
        {
            "item_code": "20277974",
            "item_name": "КОМПЛИМЕНТ Полка, 75x58 см, белый",
            "url": "https://www.ikea.com/ru/ru/p/-20277974",
            "rate": 400,
            "weight": 4.66,
        },
        {
            "item_code": "40277973",
            "item_name": "КОМПЛИМЕНТ Полка, 50x58 см, белый",
            "url": "https://www.ikea.com/ru/ru/p/-40277973",
            "rate": 300,
            "weight": 2.98,
        },
        {
            "item_code": "40366634",
            "item_name": "КОМПЛИМЕНТ Ящик, 75x58 см, белый",
            "url": "https://www.ikea.com/ru/ru/p/-40366634",
            "rate": 1700,
            "weight": 7.72,
        },
        {
            "item_code": "50121575",
            "item_name": "ПАКС Каркас гардероба, 75x58x236 см, белый",
            "url": "https://www.ikea.com/ru/ru/p/-50121575",
            "rate": 3600,
            "weight": 46.8,
        },
        {
            "item_code": "50366596",
            "item_name": "КОМПЛИМЕНТ Штанга платяная, 50 см, белый",
            "url": "https://www.ikea.com/ru/ru/p/-50366596",
            "rate": 200,
            "weight": 0.3,
        },
    ]

    res: list[Item] = []
    for i in test_data:
        doc = get_doc(Item, i)
        doc.db_insert()
        res.append(doc)
    return res


@pytest.fixture
def item_no_children():
    return get_doc(
        Item,
        {
            "item_code": "29128569",
            "item_name": "ПАКС, Гардероб, 175x58x236 см, белый",
            "url": "https://www.ikea.com/ru/ru/p/-s29128569",
            "rate": 17950,
            "child_items": [],
        },
    )


@pytest.fixture
def item(item_no_children: Item):
    item_no_children.extend(
        "child_items",
        [
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
    )
    return item_no_children


@pytest.fixture
def item_category():
    return get_doc(
        ItemCategory,
        {
            "name": "Столешницы",
            "url": "https://www.ikea.com/ru/ru/cat/-11844",
            "doctype": "Item Category",
        },
    )


@pytest.fixture
def accounts():
    frappe.db.sql("DELETE FROM tabAccount")
    initialize_accounts()


@pytest.fixture
@pytest.mark.usefixtures("accounts")
def gl_entry(payment_sales: Payment):
    payment_sales.db_insert()
    return get_doc(
        GLEntry,
        {
            "name": "GLE-2021-00001",
            "owner": "Administrator",
            "account": "Delivery",
            "debit": 0,
            "credit": 300,
            "voucher_type": "Payment",
            "voucher_no": "ebd35a9cc9",
        },
    )


@pytest.fixture
def payment_sales(sales_order: SalesOrder):
    sales_order.db_insert()
    return get_doc(
        Payment,
        {
            "name": "ebd35a9cc9",
            "docstatus": 0,
            "voucher_type": "Sales Order",
            "voucher_no": "SO-2021-0001",
            "amount": 5000,
            "paid_with_cash": False,
        },
    )


@pytest.fixture
def payment_purchase(purchase_order: PurchaseOrder):
    purchase_order.db_insert()
    return get_doc(
        Payment,
        {
            "name": "ebd35a9cc9",
            "docstatus": 0,
            "voucher_type": "Purchase Order",
            "voucher_no": "Август-1",
            "amount": 5000,
            "paid_with_cash": False,
        },
    )


@pytest.fixture
def receipt_sales(sales_order: SalesOrder):
    sales_order.db_insert()
    sales_order.db_update_all()
    return get_doc(
        Receipt, {"voucher_type": sales_order.doctype, "voucher_no": sales_order.name}
    )


@pytest.fixture
def receipt_purchase(purchase_order: PurchaseOrder):
    purchase_order.db_insert()
    purchase_order.db_update_all()
    return get_doc(
        Receipt,
        {"voucher_type": purchase_order.doctype, "voucher_no": purchase_order.name},
    )


@pytest.fixture
def sales_order(
    customer: Customer,
    child_items: list[Item],
    item: Item,
    commission_settings: CommissionSettings,
):
    customer.db_insert()
    item.set_new_name(set_child_names=True)
    item.set_parent_in_children()
    item.db_insert()
    all_children: list[TypedDocument] = item.get_all_children()  # type: ignore
    for child in all_children:
        child.db_insert()
    commission_settings.insert()
    return get_doc(
        SalesOrder,
        {
            "name": "SO-2021-0001",
            "customer": "Pavel Durov",
            "edit_commission": 0,
            "discount": 0,
            "paid_amount": 0,
            "services": [
                {"type": "Delivery to Entrance", "rate": 300},
                {"type": "Installation", "rate": 500},
            ],
            "items": [
                {"item_code": item.item_code, "qty": 1},
                {"item_code": child_items[0].item_code, "qty": 2},
            ],
        },
    )


mock_delivery_services = GetDeliveryServicesResponse(
    delivery_options=[
        DeliveryOptionDict(
            delivery_date=date(2021, 8, 26),
            delivery_type="Доставка",
            price=3299,
            service_provider=None,
            unavailable_items=[
                UnavailableItemDict(item_code="50366596", available_qty=0),
                UnavailableItemDict(item_code="10366598", available_qty=0),
                UnavailableItemDict(item_code="29128569", available_qty=0),
            ],
        ),
        DeliveryOptionDict(
            delivery_date=date(2021, 8, 26),
            delivery_type="Доставка без подъёма",
            price=2799,
            service_provider=None,
            unavailable_items=[
                UnavailableItemDict(item_code="50366596", available_qty=0),
                UnavailableItemDict(item_code="10366598", available_qty=0),
                UnavailableItemDict(item_code="29128569", available_qty=0),
            ],
        ),
        DeliveryOptionDict(
            delivery_date=date(2021, 8, 27),
            delivery_type="Пункт самовывоза",
            price=1998,
            service_provider="Деловые линии",
            unavailable_items=[
                UnavailableItemDict(item_code="50366596", available_qty=0),
                UnavailableItemDict(item_code="40277973", available_qty=0),
                UnavailableItemDict(item_code="10366598", available_qty=0),
                UnavailableItemDict(item_code="29128569", available_qty=0),
            ],
        ),
        DeliveryOptionDict(
            delivery_date=date(2021, 8, 25),
            delivery_type="Магазин",
            price=999999,
            service_provider=None,
            unavailable_items=[
                UnavailableItemDict(item_code="50366596", available_qty=0),
                UnavailableItemDict(item_code="40277973", available_qty=0),
                UnavailableItemDict(item_code="10366598", available_qty=0),
                UnavailableItemDict(item_code="29128569", available_qty=0),
            ],
        ),
        DeliveryOptionDict(
            delivery_date=date(2021, 8, 24),
            delivery_type="Магазин",
            price=1998,
            service_provider=None,
            unavailable_items=[
                UnavailableItemDict(item_code="50366596", available_qty=0),
                UnavailableItemDict(item_code="40277973", available_qty=0),
                UnavailableItemDict(item_code="10366598", available_qty=0),
                UnavailableItemDict(item_code="29128569", available_qty=0),
            ],
        ),
        DeliveryOptionDict(
            delivery_date=date(2021, 8, 24),
            delivery_type="Магазин",
            price=1998,
            service_provider=None,
            unavailable_items=[
                UnavailableItemDict(item_code="50366596", available_qty=0),
                UnavailableItemDict(item_code="10366598", available_qty=0),
                UnavailableItemDict(item_code="29128569", available_qty=0),
            ],
        ),
        DeliveryOptionDict(
            delivery_date=date(2021, 8, 25),
            delivery_type="Магазин",
            price=1998,
            service_provider=None,
            unavailable_items=[
                UnavailableItemDict(item_code="50366596", available_qty=0),
                UnavailableItemDict(item_code="40277973", available_qty=0),
                UnavailableItemDict(item_code="10366598", available_qty=0),
                UnavailableItemDict(item_code="29128569", available_qty=0),
            ],
        ),
    ],
    cannot_add=["50366596"],
)


mock_purchase_info = PurchaseInfoDict(
    purchase_date="2021-04-19",
    delivery_date="2021-04-24",
    delivery_cost=399.0,
    total_cost=7927.0,
)


def patch_get_delivery_services(monkeypatch: pytest.MonkeyPatch):
    mock_get_delivery_services: Callable[
        [Any, Any, Any], Any
    ] = lambda api, items, zip_code: mock_delivery_services
    monkeypatch.setattr(
        ikea_api_wrapped, "get_delivery_services", mock_get_delivery_services
    )


@pytest.fixture
def purchase_order(sales_order: SalesOrder, monkeypatch: pytest.MonkeyPatch):

    sales_order.set_child_items()
    if not doc_exists(sales_order.doctype, sales_order.name):
        sales_order.db_insert()
        sales_order.db_update_all()

    patch_get_delivery_services(monkeypatch)

    return get_doc(
        PurchaseOrder,
        {
            "name": "Август-1",
            "docstatus": 0,
            "status": "Draft",
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
        },
    )


@pytest.fixture
def commission_settings():
    return get_doc(
        CommissionSettings,
        {
            "name": "Commission Settings",
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
        },
    )


mock_token = (
    "eyJhbGciOiJSUzIre8NiIsInR5cCI6IkpXVCIsImtpZCI6ImVxSFFLR3duR3"
    + "hfV3dJZkx0RGpaeDA5MTUzS2xSam5fVE1nVUlMYlJ5RncifQ.eyJpc3MiOiJ"
    + "odHRwczovL2FwaS5pbmdrYS5pa2VhLmNvbS9ndWVzdCIsInN1YiI6ImRiOWU"
    + "yMzg3LTU3ZDAtNGZiYS1iNzhjLTdiZmYwOWEyMGJlNCIsInJldGFpbFVuaXQ"
    + "iOiJydSIsImlhdCI6MTYyOTcyOTE2MiwiZXhwIjoxNjMyMzIxMTYyfQ.UAkv"
    + "ZmlX9sj8Hgve1kkq7tcf73-aDshLusxnAsW-1-9izS14cPGehzX47-MyResL"
    + "jwlr7W70t0jMjL8ihdgj5aVSl-W3UVw_tt8FfO60b-GDfMt_vCAyAk2N9lts"
    + "n7Ql5NiQXeTM6NVDLCCBM27FAUuTiDVEJc-F7WgmXWip4nE"
)


@pytest.fixture
def ikea_settings(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(ikea_api.auth, "get_guest_token", lambda: mock_token)
    mock_get_authorized_token: Callable[
        [Any, Any], str
    ] = lambda username, password: mock_token
    monkeypatch.setattr(
        ikea_api.auth, "get_authorized_token", mock_get_authorized_token
    )

    doc = get_doc(IkeaSettings)
    doc.zip_code = "101000"
    doc.save()
    return doc


@pytest.fixture
def parsed_item() -> ParsedItem:
    return {
        "is_combination": True,
        "item_code": "29128569",
        "name": "ПАКС, Гардероб, 175x58x236 см, белый",
        "image_url": "https://www.ikea.com/ru/ru/images/products/paks-garderob-belyj__0383288_PE557277_S5.JPG",
        "weight": 0.0,
        "child_items": [
            {
                "item_code": "10014030",
                "item_name": "ПАКС, Каркас гардероба, 175x58x236 см, белый",
                "weight": 41.3,
                "qty": 2,
            },
            {
                "item_code": "10366598",
                "item_name": "КОМПЛИМЕНТ, Штанга платяная, 175x58x236 см, белый",
                "weight": 0.43,
                "qty": 1,
            },
            {
                "item_code": "20277974",
                "item_name": "КОМПЛИМЕНТ, Полка, 175x58x236 см, белый",
                "weight": 4.66,
                "qty": 2,
            },
            {
                "item_code": "40277973",
                "item_name": "КОМПЛИМЕНТ, Полка, 175x58x236 см, белый",
                "weight": 2.98,
                "qty": 6,
            },
            {
                "item_code": "40366634",
                "item_name": "КОМПЛИМЕНТ, Ящик, 175x58x236 см, белый",
                "weight": 7.72,
                "qty": 3,
            },
            {
                "item_code": "50121575",
                "item_name": "ПАКС, Каркас гардероба, 175x58x236 см, белый",
                "weight": 46.8,
                "qty": 1,
            },
            {
                "item_code": "50366596",
                "item_name": "КОМПЛИМЕНТ, Штанга платяная, 175x58x236 см, белый",
                "weight": 0.3,
                "qty": 1,
            },
        ],
        "price": 17950,
        "url": "https://www.ikea.com/ru/ru/p/-s29128569",
        "category_name": "Открытые гардеробы",
        "category_url": "https://www.ikea.com/ru/ru/cat/-43634",
    }


@pytest.fixture
def checkout(purchase_order: PurchaseOrder):
    purchase_order.db_insert()
    purchase_order.db_update_all()
    return get_doc(Checkout, {"purchase_order": purchase_order.name})


class FakeBot(MagicMock):
    def send_message(self, *args: Any, **kwargs: Any):
        pass

    def get_updates(self):
        return [
            SimpleNamespace(
                **{
                    "my_chat_member": SimpleNamespace(
                        **{
                            "old_chat_member": {
                                "status": "left",
                                "user": SimpleNamespace(
                                    **{
                                        "id": 428190844,
                                        "username": "some_random_test_bot_name_bot",
                                        "is_bot": True,
                                        "first_name": "Yet Another Test Bot",
                                    }
                                ),
                                "until_date": None,
                            },
                            "new_chat_member": SimpleNamespace(
                                **{
                                    "can_be_edited": False,
                                    "can_change_info": True,
                                    "is_anonymous": False,
                                    "can_edit_messages": True,
                                    "can_delete_messages": True,
                                    "can_manage_chat": True,
                                    "status": "administrator",
                                    "can_restrict_members": True,
                                    "user": SimpleNamespace(
                                        **{
                                            "id": 428190844,
                                            "username": "some_random_test_bot_name_bot",
                                            "is_bot": True,
                                            "first_name": "Yet Another Test Bot",
                                        }
                                    ),
                                    "can_manage_voice_chats": True,
                                    "can_post_messages": True,
                                    "can_invite_users": True,
                                    "can_promote_members": False,
                                    "until_date": None,
                                }
                            ),
                            "chat": SimpleNamespace(
                                **{
                                    "id": -249104912890,
                                    "title": "Test Channel",
                                    "type": "channel",
                                }
                            ),
                            "date": 1630059515,
                            "from": SimpleNamespace(
                                **{
                                    "language_code": "en",
                                    "id": 248091841,
                                    "username": "some_random_username",
                                    "is_bot": False,
                                    "first_name": "John",
                                }
                            ),
                        }
                    ),
                    "update_id": 839065573,
                }
            )
        ]


@pytest.fixture
def telegram_settings(monkeypatch: pytest.MonkeyPatch) -> TelegramSettings:
    monkeypatch.setattr("telegram.Bot", FakeBot)
    doc = get_doc(TelegramSettings)
    doc.bot_token = "28910482:82359djtg3fi0denjk"
    doc.chat_id = "-103921437849"
    doc.save()
    return doc


@pytest.fixture
def delivery_trip(sales_order: SalesOrder):
    sales_order.db_insert()
    sales_order.db_update_all()
    return get_doc(
        DeliveryTrip,
        {
            "stops": [
                {
                    "doctype": "Delivery Stop",
                    "sales_order": "SO-2021-0001",
                    "address": "Arbat, 1",
                    "pending_amount": 700,
                    "customer": "Pavel Durov",
                    "city": "Moscow",
                    "phone": "89115553535",
                    "delivery_type": "To Apartment",
                    "installation": True,
                }
            ],
        },
    )


@pytest.fixture
def sales_return(sales_order: SalesOrder):
    sales_order.update_items_from_db()
    sales_order.set_child_items()
    sales_order.calculate()
    sales_order.db_insert()
    sales_order.db_update_all()
    return get_doc(
        SalesReturn,
        {
            "sales_order": sales_order.name,
            "items": [
                {
                    "item_code": "10366598",
                    "item_name": "КОМПЛИМЕНТ Штанга платяная, 75 см, белый",
                    "qty": 1,
                    "rate": 250,
                },
                {
                    "item_code": "40366634",
                    "item_name": "КОМПЛИМЕНТ Ящик, 75x58 см, белый",
                    "qty": 1,
                    "rate": 1700,
                },
            ],
        },
    )


@pytest.fixture
def purchase_return(purchase_order: PurchaseOrder, sales_order: SalesOrder):
    sales_order.save()
    purchase_order.db_insert()
    purchase_order.db_update_all()
    return get_doc(
        PurchaseReturn,
        {
            "purchase_order": purchase_order.name,
            "items": [
                {
                    "item_code": "10366598",
                    "item_name": "КОМПЛИМЕНТ Штанга платяная, 75 см, белый",
                    "qty": 2,
                    "rate": 250,
                },
                {
                    "item_code": "40366634",
                    "item_name": "КОМПЛИМЕНТ Ящик, 75x58 см, белый",
                    "qty": 1,
                    "rate": 1700,
                },
            ],
        },
    )
