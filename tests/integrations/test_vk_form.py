from __future__ import annotations

from copy import copy
from datetime import datetime
from typing import Any

import pytest
import sentry_sdk
from werkzeug import Response

import comfort.integrations.vk_form
import frappe
from comfort.comfort_core import CommissionSettings, VkFormSettings
from comfort.entities import Customer, Item
from comfort.integrations.vk_form import (
    _create_sales_order,
    _create_vk_group_dialog_url,
    _get_customer_name,
    _get_delivery_service,
    _send_confirmation_message,
    main,
    process_form,
)
from comfort.transactions import SalesOrder
from comfort.utils import count_qty, doc_exists, get_doc
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
        ("До подъезда (от 150 ₽)", {"type": "Delivery to Entrance", "rate": 150}),
        ("До квартиры (от 400 ₽)", {"type": "Delivery to Apartment", "rate": 400}),
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
    doc = get_doc(SalesOrder, f"SO-{datetime.now().year}-0001")
    assert doc.customer == customer.name
    assert dict(count_qty(doc.items)) == {item_no_children.item_code: 1}


def test_vk_form_create_sales_order_no_items():
    _create_sales_order("John Johnson", "", "")
    assert not doc_exists("Sales Order", f"SO-{datetime.now().year}-0001")


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
        customer.name, item_no_children.item_code, "До подъезда (от 150 ₽)"
    )
    doc = get_doc(SalesOrder, f"SO-{datetime.now().year}-0001")
    assert doc.services[0].type == "Delivery to Entrance"
    assert doc.services[0].rate == 150


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
    doc = get_doc(SalesOrder, f"SO-{datetime.now().year}-0001")
    assert not doc.services


@pytest.fixture
def vk_form_settings():
    doc = get_doc(VkFormSettings)
    doc.api_secret = mock_api_secret
    doc.group_id = mock_group_id
    doc.save()


def test_send_confirmation_message(monkeypatch: pytest.MonkeyPatch):
    exp_message = "Иван, спасибо за ваш заказ! Когда обработаем его, напишем вам!"
    exp_user_id = 1
    called = False

    class CustomVkApi:
        def send_message(self, user_id: int, message: str):
            nonlocal called
            called = True
            assert message == exp_message
            assert user_id == exp_user_id

    monkeypatch.setattr(comfort.integrations.vk_form, "VkApi", CustomVkApi)
    _send_confirmation_message(1, "Иван")
    assert called


@pytest.mark.usefixtures("vk_form_settings")
# patch Customer object to disable vk info fetching
@pytest.mark.usefixtures("customer")
def test_process_form(
    monkeypatch: pytest.MonkeyPatch,
    item_no_children: Item,
    commission_settings: CommissionSettings,
):
    item_no_children.db_insert()
    commission_settings.insert()
    patch_fetch_items(monkeypatch)
    called_send_confirmation_message = False

    def mock_send_confirmation_message(user_id: int, first_name: str):
        assert user_id == 111111111
        assert first_name == "Ivan"
        nonlocal called_send_confirmation_message
        called_send_confirmation_message = True

    monkeypatch.setattr(
        comfort.integrations.vk_form,
        "_send_confirmation_message",
        mock_send_confirmation_message,
    )

    process_form(mock_form)
    assert called_send_confirmation_message
    doc = get_doc(SalesOrder, f"SO-{datetime.now().year}-0001")
    assert doc.customer
    assert doc.items
    assert doc.services


def test_vk_form_main_whitelisted():
    frappe.is_whitelisted(main)


def test_vk_form_main_success(monkeypatch: pytest.MonkeyPatch):
    called_process_form = False

    form_dict = {"test": "test"}

    def mock_process_form(form: dict[Any, Any]):
        assert form == frappe.form_dict == form_dict
        nonlocal called_process_form
        called_process_form = True

    monkeypatch.setattr(comfort.integrations.vk_form, "process_form", mock_process_form)

    user_before = copy(frappe.session.user)
    frappe.session.user = "Guest"
    frappe.form_dict = form_dict
    resp = main()

    assert frappe.session.user == "Administrator"
    assert frappe.session.sid == "Administrator"
    frappe.session.user = user_before
    assert called_process_form
    assert type(resp) == Response
    assert resp.get_data(as_text=True) == "ok"


def test_vk_form_main_failure(monkeypatch: pytest.MonkeyPatch):
    called_process_form = False
    called_capture_exception = False

    def mock_process_form(form: dict[Any, Any]):
        nonlocal called_process_form
        called_process_form = True
        raise ValueError

    def mock_capture_exception(error: Exception):
        nonlocal called_capture_exception
        called_capture_exception = True
        assert type(error) == ValueError

    monkeypatch.setattr(comfort.integrations.vk_form, "process_form", mock_process_form)
    monkeypatch.setattr(sentry_sdk, "capture_exception", mock_capture_exception)

    user_before = copy(frappe.session.user)
    frappe.session.user = "Guest"
    resp = main()
    assert frappe.session.user == "Administrator"
    assert frappe.session.sid == "Administrator"
    frappe.session.user = user_before
    assert called_process_form
    assert called_capture_exception
    assert type(resp) == Response
    assert resp.get_data(as_text=True) == "ok"
