from __future__ import annotations

import pytest

import comfort.integrations.vk_form
from comfort import count_qty, doc_exists, get_doc
from comfort.comfort_core.doctype.commission_settings.commission_settings import (
    CommissionSettings,
)
from comfort.comfort_core.doctype.vk_form_settings.vk_form_settings import (
    VkFormSettings,
)
from comfort.entities.doctype.customer.customer import Customer
from comfort.entities.doctype.item.item import Item
from comfort.integrations.vk_form import (
    _create_sales_order,
    _create_vk_group_dialog_url,
    _get_customer_name,
    _get_delivery_service,
    process_form,
)
from comfort.transactions.doctype.sales_order.sales_order import SalesOrder
from tests.integrations.test_browser_ext_server import patch_fetch_items

mock_api_secret = "E64XhVwb84nf@wPumC.JXFMo"  # nosec
mock_group_id = 11111111
mock_form = {
    "type": "lead_forms_new",
    "object": {
        "lead_id": 39842910,
        "group_id": mock_group_id,
        "user_id": 111111111,
        "form_id": 1,
        "form_name": "Оформить заказ",
        "answers": [
            {"key": "first_name", "question": "First name", "answer": "Ivan"},
            {"key": "last_name", "question": "Last name", "answer": "Ivanov"},
            {
                "key": "phone_number",
                "question": "Phone number",
                "answer": "+7 (800) 555-35-35",
            },
            {
                "key": "custom_0",
                "question": "Ваш заказ в виде «ссылка или артикул — количество»",
                "answer": "29128569",
            },
            {
                "key": "custom_1",
                "question": "Доставка",
                "answer": "До подъезда (100 ₽)",
            },
        ],
    },
    "group_id": mock_group_id,
    "event_id": "2938fij092r8390dhjskhfqeu092",
    "secret": mock_api_secret,
}


@pytest.mark.parametrize(
    ("first_name", "second_name", "exp_result"),
    (("Ivan", "Ivanov", "Ivan Ivanov"), ("Ivan", "", "Ivan")),
)
def test_get_customer_name(first_name: str, second_name: str, exp_result: str):
    assert _get_customer_name(first_name, second_name) == exp_result


def test_create_vk_group_dialog_url():
    assert (
        _create_vk_group_dialog_url(11111111, 11111111)
        == "https://vk.com/gim11111111?sel=11111111"
    )


@pytest.mark.parametrize(
    ("raw_delivery_type", "exp_result"),
    (
        ("Самовывоз (бесплатно)", None),
        ("До подъезда (100 ₽)", {"type": "Delivery to Entrance", "rate": 100}),
        ("До квартиры (от 300 ₽)", {"type": "Delivery to Apartment", "rate": 300}),
    ),
)
def test_get_delivery_service(
    raw_delivery_type: str, exp_result: dict[str, str | int] | None
):
    assert _get_delivery_service(raw_delivery_type) == exp_result


def patch_fetch_items(monkeypatch: pytest.MonkeyPatch):
    def mock_fetch_items(item_codes: str, force_update: bool):
        return {"successful": [item_codes]}

    monkeypatch.setattr(comfort.integrations.vk_form, "fetch_items", mock_fetch_items)


def test_vk_form_create_sales_order_with_items(
    monkeypatch: pytest.MonkeyPatch,
    customer: Customer,
    item_no_children: Item,
    commission_settings: CommissionSettings,
):
    customer.db_insert()
    item_no_children.db_insert()
    commission_settings.insert()
    patch_fetch_items(monkeypatch)

    _create_sales_order(customer.name, item_no_children.item_code, "")
    doc = get_doc(SalesOrder, "SO-2021-0001")
    assert doc.customer == customer.name
    assert dict(count_qty(doc.items)) == {item_no_children.item_code: 1}


def test_vk_form_create_sales_order_no_items():
    _create_sales_order("John Johnson", "", "")
    assert not doc_exists("Sales Order", "SO-2021-0001")


def test_vk_form_create_sales_order_with_services(
    monkeypatch: pytest.MonkeyPatch,
    customer: Customer,
    item_no_children: Item,
    commission_settings: CommissionSettings,
):
    customer.db_insert()
    item_no_children.db_insert()
    commission_settings.insert()
    patch_fetch_items(monkeypatch)

    _create_sales_order(
        customer.name, item_no_children.item_code, "До подъезда (100 ₽)"
    )
    doc = get_doc(SalesOrder, "SO-2021-0001")
    assert doc.services[0].type == "Delivery to Entrance"
    assert doc.services[0].rate == 100


def test_vk_form_create_sales_order_no_services(
    monkeypatch: pytest.MonkeyPatch,
    customer: Customer,
    item_no_children: Item,
    commission_settings: CommissionSettings,
):
    customer.db_insert()
    item_no_children.db_insert()
    commission_settings.insert()
    patch_fetch_items(monkeypatch)

    _create_sales_order(customer.name, item_no_children.item_code, "")
    doc = get_doc(SalesOrder, "SO-2021-0001")
    assert not doc.services


@pytest.fixture
def vk_form_settings():
    doc = get_doc(VkFormSettings)
    doc.api_secret = mock_api_secret
    doc.group_id = mock_group_id
    doc.save()


@pytest.mark.usefixtures("vk_form_settings")
@pytest.mark.usefixtures(
    "customer"
)  # patch Customer object to disable vk info fetching
def test_process_form(
    monkeypatch: pytest.MonkeyPatch,
    item_no_children: Item,
    commission_settings: CommissionSettings,
):
    item_no_children.db_insert()
    commission_settings.insert()
    patch_fetch_items(monkeypatch)

    process_form(mock_form)
    doc = get_doc(SalesOrder, "SO-2021-0001")
    assert doc.customer
    assert doc.items
    assert doc.services
