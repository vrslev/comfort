from __future__ import annotations

from copy import copy
from types import SimpleNamespace
from typing import Any

import pytest
import responses

import frappe
from comfort.entities.doctype.customer.customer import (
    Customer,
    _get_vk_users_for_customers,
    _update_customer_from_vk_user,
    _vk_token_in_settings,
    parse_vk_url,
    update_all_customers_from_vk,
)
from comfort.integrations.vk_api import User, VkApi
from comfort.utils import new_doc
from tests.integrations import test_vk_api

acceptable_vk_urls = (
    "https://vk.com/im?sel=1",
    "https://vk.com/im?media=&sel=1",
    "https://vk.com/im?media=&sel=18392044",
    "https://vk.com/gim1111111?sel=1",
    "https://vk.com/gim1111111?media=&sel=1",
    "https://vk.com/gim1111111?media=&sel=18392044",
)
expected_vk_ids = ("1", "1", "18392044", "1", "1", "18392044")
expected_vk_urls = (
    "im?sel=1",
    "im?sel=1",
    "im?sel=18392044",
    "gim1111111?sel=1",
    "gim1111111?sel=1",
    "gim1111111?sel=18392044",
)


@pytest.mark.parametrize(
    ("input", "id", "url"),
    zip(acceptable_vk_urls, expected_vk_ids, expected_vk_urls),
)
def test_parse_vk_id_passes(input: str, id: str, url: str):
    assert parse_vk_url(input) == (id, f"https://vk.com/{url}")


@pytest.mark.parametrize(
    "url",
    (
        "example.com",
        "https://example.com/im?sel=1",
        "vk.com",
        "https://vk.com",
        "https://vk.com/im",
        "https://vk.com/gim",
        "https://vk.com/sel",
        "https://vk.com/im?sel",
        "https://vk.com/im",
        "https://vk.com/gim",
        "https://vk.com/sel",
        "https://vk.com/im?sel",
        "https://vk.com/gim?sel",
    ),
)
def test_parse_vk_id_raises(url: str):
    with pytest.raises(frappe.ValidationError, match="Invalid VK URL"):
        parse_vk_url(url)


@pytest.mark.parametrize(
    ("input", "expected"),
    (
        ("John Johnson", "John Johnson"),
        (" John Johnson", "John Johnson"),
        (" John Johnson ", "John Johnson"),
        ("John Johnson ", "John Johnson"),
    ),
)
def test_customer_before_insert_not_extsts(
    customer: Customer, input: str, expected: str
):
    customer.name = input
    customer.before_insert()
    assert customer.name == expected


@pytest.mark.usefixtures("vk_api_settings")
def test_vk_token_in_settings_true():
    frappe.message_log = []
    assert _vk_token_in_settings()
    assert frappe.message_log == []


def test_vk_token_in_settings_false():
    frappe.message_log = []
    assert not _vk_token_in_settings()
    assert "Enter VK App service token in Vk Api Settings" in str(frappe.message_log)
    frappe.message_log = []


@pytest.mark.parametrize(
    ("input", "expected"),
    (
        ("John Johnson", "John Johnson 2"),
        (" John Johnson", "John Johnson 2"),
        ("John Johnson 2", "John Johnson 3"),
        ("John Johnson 9", "John Johnson 10"),
        ("John Johnson 10", "John Johnson 11"),
        ("John Johnson 19", "John Johnson 20"),
        ("John Johnson 99", "John Johnson 100"),
        (" John Johnson 99", "John Johnson 100"),
    ),
)
def test_customer_before_insert_exists(customer: Customer, input: str, expected: str):
    doc = new_doc(Customer)
    doc.name = copy(input)
    doc.db_insert()

    customer.name = copy(input)
    customer.before_insert()
    assert customer.name == expected


@responses.activate
@pytest.mark.usefixtures("vk_api_settings")
def test_get_vk_users_for_customers():
    vk_api = VkApi()

    params = {"user_ids": [1, 2], "fields": ["photo_max_orig", "sex", "city"]}
    test_vk_api.add_mock_response(
        vk_api, "users.get", vk_api._get_params(params), test_vk_api.mock_users_get_resp
    )

    customers = (
        SimpleNamespace(name="Иван Иванов", vk_id=1),
        SimpleNamespace(name="Елена Иванова", vk_id=2),
    )
    payload: list[Any] = list(customers)
    payload.append(SimpleNamespace(name="Nobody", vk_id=None))
    users = _get_vk_users_for_customers(payload)

    for idx, user_resp in enumerate(test_vk_api.mock_users_get_resp["response"]):
        assert users[str(customers[idx].vk_id)] == User(**user_resp)


@responses.activate
def test_get_vk_users_for_customers_no_user_ids():
    customers: tuple[Any] = (SimpleNamespace(name="Иван Иванов", vk_id=None),)
    assert _get_vk_users_for_customers(customers) == {}


@pytest.mark.parametrize(
    ("sex", "expected"), ((None, None), (0, None), (1, "Female"), (2, "Male"))
)
def test_update_customer_from_vk_user_gender_not_set(
    customer: Customer, sex: Any, expected: Any
):
    customer.gender = None
    user: Any = SimpleNamespace(sex=sex, photo_max_orig=None, city=None)
    _update_customer_from_vk_user(customer, user)
    assert customer.gender == expected


def test_update_customer_from_vk_user_gender_set(customer: Customer):
    customer.gender = "Male"
    user: Any = SimpleNamespace(sex=1, photo_max_orig=None, city=None)
    _update_customer_from_vk_user(customer, user)
    assert customer.gender == "Male"


def test_update_customer_from_vk_user_image(customer: Customer):
    image = "https://example.com/image.jpg"
    user: Any = SimpleNamespace(sex=None, photo_max_orig=image, city=None)
    _update_customer_from_vk_user(customer, user)
    assert customer.image == image


def test_update_customer_from_vk_user_city_not_set(customer: Customer):
    customer.city = None
    city = "Moscow"
    user: Any = SimpleNamespace(
        sex=None, photo_max_orig=None, city=SimpleNamespace(id=1, title=city)
    )
    _update_customer_from_vk_user(customer, user)
    assert customer.city == city


def test_update_customer_from_vk_user_city_set(customer: Customer):
    customer.city = "Moscow"
    user: Any = SimpleNamespace(
        sex=None, photo_max_orig=None, city=SimpleNamespace(id=1, title="Not Moscow")
    )
    _update_customer_from_vk_user(customer, user)
    assert customer.city == "Moscow"


@responses.activate
@pytest.mark.usefixtures("vk_api_settings")
def test_update_all_customers_from_vk_with_vk_id(customer: Customer):
    customer.gender = None
    customer.city = None
    customer.db_insert()

    doc = new_doc(Customer)
    doc.name = "Test Name"
    doc.db_insert()

    image = "https://example.com/image.jpg"
    city = "Moscow"
    gender = "Female"

    vk_api = VkApi()
    params = {"user_ids": [customer.vk_id], "fields": ["photo_max_orig", "sex", "city"]}
    response = {
        "response": [
            {
                "id": 1,
                "first_name": "Pavel",
                "last_name": "Durov",
                "is_closed": False,
                "can_access_closed": False,
                "sex": 1,
                "photo_max_orig": image,
                "city": {"id": 1, "title": city},
            }
        ]
    }
    test_vk_api.add_mock_response(
        vk_api, "users.get", vk_api._get_params(params), response
    )

    update_all_customers_from_vk()
    customer.reload()
    assert customer.image == image
    assert customer.city == city
    assert customer.gender == gender


@responses.activate
def test_update_all_customers_from_vk_no_vk_id(customer: Customer):
    customer.vk_id = None
    customer.db_insert()
    customer.reload()
    doc_before = customer.as_dict()

    update_all_customers_from_vk()
    customer.reload()
    assert customer.as_dict() == doc_before
