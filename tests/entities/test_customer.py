from __future__ import annotations

from copy import copy
from types import SimpleNamespace

import pytest
import responses

import comfort.entities.doctype.customer.customer
from comfort import new_doc
from comfort.entities.doctype.customer.customer import (
    Customer,
    _get_vk_users_for_customers,
    _update_customer_from_vk_user,
    parse_vk_id,
    update_all_customers_from_vk,
)
from comfort.integrations.vk_api import User, VkApi
from frappe import ValidationError
from tests.integrations import test_vk_api

acceptable_vk_urls = (
    "https://vk.com/im?sel=1",
    "https://vk.com/im?media=&sel=1",
    "https://vk.com/im?media=&sel=18392044",
    "https://vk.com/gim?sel=1",
    "https://vk.com/gim?media=&sel=1",
    "https://vk.com/gim?media=&sel=18392044",
    None,
)
expected_vk_ids = ("1", "1", "18392044", "1", "1", "18392044", None)


@pytest.mark.parametrize("vk_url,vk_id", zip(acceptable_vk_urls, expected_vk_ids))
def test_parse_vk_id_passes(vk_url: str | None, vk_id: str | None):
    assert parse_vk_id(vk_url) == vk_id


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
        parse_vk_id(vk_url)


def test_customer_validate(customer: Customer):
    called = False

    def mock_update_info_from_vk():
        nonlocal called
        called = True

    customer.update_info_from_vk = mock_update_info_from_vk

    customer.validate()
    assert customer.vk_id == "1"
    assert called


@pytest.mark.parametrize(("vk_id", "exp_called"), (("248934423", True), (None, False)))
def test_update_info_from_vk(
    monkeypatch: pytest.MonkeyPatch, customer: Customer, vk_id: str, exp_called: bool
):
    customer = Customer(customer.as_dict())  # Customer is patched in conftest

    first_called = False
    second_called = False
    exp_user = "User"

    def mock_get_vk_users_for_customers(customers: tuple[Customer]):
        nonlocal first_called
        first_called = True
        return {customer.vk_id: exp_user}

    def mock_update_customer_from_vk_user(customer: Customer, user: str):
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
def test_update_customer_from_vk_user_gender(
    customer: Customer, sex: int | None, exp_gender: str | None
):
    user = SimpleNamespace(sex=sex, photo_max_orig=None, city=None)
    _update_customer_from_vk_user(customer, user)  # type: ignore
    assert customer.gender == exp_gender


def test_update_customer_from_vk_user_image(customer: Customer):
    image = "https://example.com/image.jpg"
    user = SimpleNamespace(sex=None, photo_max_orig=image, city=None)
    _update_customer_from_vk_user(customer, user)  # type: ignore
    assert customer.image == image


def test_update_customer_from_vk_user_city(customer: Customer):
    city = "Moscow"
    user = SimpleNamespace(
        sex=None, photo_max_orig=None, city=SimpleNamespace(id=1, title=city)
    )
    _update_customer_from_vk_user(customer, user)  # type: ignore
    assert customer.city == city


@responses.activate
@pytest.mark.usefixtures("vk_api_settings")
def test_update_all_customers_from_vk_with_vk_id(customer: Customer):
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
