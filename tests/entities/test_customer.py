from __future__ import annotations

from copy import copy
from types import SimpleNamespace
from typing import Any

import pytest
import responses

import comfort.entities.doctype.customer.customer
import frappe
from comfort import new_doc
from comfort.comfort_core.doctype.vk_api_settings.vk_api_settings import VkApiSettings
from comfort.entities.doctype.customer.customer import (
    Customer,
    _get_vk_users_for_customers,
    _update_customer_from_vk_user,
    parse_vk_url,
    update_all_customers_from_vk,
)
from comfort.integrations.vk_api import User, VkApi
from frappe import ValidationError
from tests.integrations import test_vk_api

acceptable_vk_urls = (
    "https://vk.com/im?sel=1",
    "https://vk.com/im?media=&sel=1",
    "https://vk.com/im?media=&sel=18392044",
    "https://vk.com/gim1111111?sel=1",
    "https://vk.com/gim1111111?media=&sel=1",
    "https://vk.com/gim1111111?media=&sel=18392044",
    None,
)
expected_vk_ids = ("1", "1", "18392044", "1", "1", "18392044", None)
expected_vk_urls = (
    "im?sel=1",
    "im?sel=1",
    "im?sel=18392044",
    "gim1111111?sel=1",
    "gim1111111?sel=1",
    "gim1111111?sel=18392044",
    None,
)


@pytest.mark.parametrize(
    ("vk_url", "vk_id", "new_url"),
    zip(acceptable_vk_urls, expected_vk_ids, expected_vk_urls),
)
def test_parse_vk_id_passes(vk_url: str | None, vk_id: str | None, new_url: str | None):
    res = parse_vk_url(vk_url)
    if vk_url is None:
        assert res is None
    else:
        assert res.vk_id == vk_id  # type: ignore
        assert res.vk_url == f"https://vk.com/{new_url}"  # type: ignore


@pytest.mark.parametrize(
    "vk_url",
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
def test_parse_vk_id_raises(vk_url: str):
    with pytest.raises(ValidationError, match="Invalid VK URL"):
        parse_vk_url(vk_url)


def test_customer_before_insert_not_extsts(customer: Customer):
    name = "John Johnson"
    customer.name = copy(name)
    customer.before_insert()
    assert customer.name == name


@pytest.mark.parametrize(
    ("input", "exp_output"),
    (
        ("John Johnson", "John Johnson 2"),
        ("John Johnson 2", "John Johnson 3"),
        ("John Johnson 9", "John Johnson 10"),
        ("John Johnson 10", "John Johnson 11"),
        ("John Johnson 19", "John Johnson 20"),
        ("John Johnson 99", "John Johnson 100"),
    ),
)
def test_customer_before_insert_exists(customer: Customer, input: str, exp_output: str):
    doc = new_doc(Customer)
    doc.name = copy(input)
    doc.db_insert()

    customer.name = copy(input)
    customer.before_insert()
    assert customer.name == exp_output


def test_customer_validate(customer: Customer):
    called = False

    def mock_update_info_from_vk():
        nonlocal called
        called = True

    customer.update_info_from_vk = mock_update_info_from_vk

    customer.validate()
    assert customer.vk_id == "1"
    assert called


@pytest.mark.usefixtures("vk_api_settings")
def test_vk_group_token_in_settings_true():
    frappe.message_log = []
    res = Customer._vk_group_token_in_settings(object())  # type: ignore
    assert res
    assert frappe.message_log == []


def test_vk_group_token_in_settings_false():
    frappe.message_log = []
    res = Customer._vk_group_token_in_settings(object())  # type: ignore
    assert not res
    assert "Enter VK App service token in Vk Api Settings" in str(frappe.message_log)  # type: ignore


@pytest.mark.parametrize(
    ("vk_id", "with_group_token", "exp_called"),
    (("248934423", True, True), ("248934423", False, False), (None, True, False)),
)
def test_update_info_from_vk(
    monkeypatch: pytest.MonkeyPatch,
    customer: Customer,
    vk_api_settings: VkApiSettings,
    vk_id: str,
    with_group_token: bool,
    exp_called: bool,
):
    customer = Customer(customer.as_dict())  # Customer class is patched in conftest

    if not with_group_token:
        vk_api_settings.group_token = None
        vk_api_settings.save()

    first_called = False
    second_called = False
    exp_user = "User"

    def mock_get_vk_users_for_customers(_: Any):
        nonlocal first_called
        first_called = True
        return {customer.vk_id: exp_user}

    def mock_update_customer_from_vk_user(_: Any, user: str):
        nonlocal second_called
        second_called = True
        assert user == exp_user

    monkeypatch.setattr(
        comfort.entities.doctype.customer.customer,
        "_get_vk_users_for_customers",
        mock_get_vk_users_for_customers,
    )
    monkeypatch.setattr(
        comfort.entities.doctype.customer.customer,
        "_update_customer_from_vk_user",
        mock_update_customer_from_vk_user,
    )

    customer.vk_id = vk_id
    customer.update_info_from_vk()

    if exp_called:
        assert first_called
        assert second_called
    else:
        assert not first_called
        assert not second_called


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
    payload = list(customers)
    payload.append(SimpleNamespace(name="Nobody", vk_id=None))
    users = _get_vk_users_for_customers(payload)  # type: ignore

    for idx, user_resp in enumerate(test_vk_api.mock_users_get_resp["response"]):
        assert users[str(customers[idx].vk_id)] == User(**user_resp)


@responses.activate
def test_get_vk_users_for_customers_no_user_ids():
    assert (
        _get_vk_users_for_customers(
            (SimpleNamespace(name="Иван Иванов", vk_id=None),),  # type: ignore
        )
        == {}
    )


@pytest.mark.parametrize(
    "sex,exp_gender", ((None, None), (0, None), (1, "Female"), (2, "Male"))
)
def test_update_customer_from_vk_user_gender_not_set(
    customer: Customer, sex: int | None, exp_gender: str | None
):
    customer.gender = None
    user = SimpleNamespace(sex=sex, photo_max_orig=None, city=None)
    _update_customer_from_vk_user(customer, user)  # type: ignore
    assert customer.gender == exp_gender


def test_update_customer_from_vk_user_gender_set(customer: Customer):
    customer.gender = "Male"
    user = SimpleNamespace(sex=1, photo_max_orig=None, city=None)
    _update_customer_from_vk_user(customer, user)  # type: ignore
    assert customer.gender == "Male"


def test_update_customer_from_vk_user_image(customer: Customer):
    image = "https://example.com/image.jpg"
    user = SimpleNamespace(sex=None, photo_max_orig=image, city=None)
    _update_customer_from_vk_user(customer, user)  # type: ignore
    assert customer.image == image


def test_update_customer_from_vk_user_city_not_set(customer: Customer):
    customer.city = None
    city = "Moscow"
    user = SimpleNamespace(
        sex=None, photo_max_orig=None, city=SimpleNamespace(id=1, title=city)
    )
    _update_customer_from_vk_user(customer, user)  # type: ignore
    assert customer.city == city


def test_update_customer_from_vk_user_city_set(customer: Customer):
    customer.city = "Moscow"
    user = SimpleNamespace(
        sex=None, photo_max_orig=None, city=SimpleNamespace(id=1, title="Not Moscow")
    )
    _update_customer_from_vk_user(customer, user)  # type: ignore
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
    doc_before = copy(customer)
    update_all_customers_from_vk()
    customer.reload()
    assert customer.as_dict() == doc_before.as_dict()
