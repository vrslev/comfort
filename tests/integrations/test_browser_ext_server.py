import re
from datetime import datetime

import pytest
from jwt import PyJWT

import comfort.integrations.browser_ext
from comfort import count_qty, get_doc
from comfort.comfort_core.doctype.commission_settings.commission_settings import (
    CommissionSettings,
)
from comfort.comfort_core.doctype.ikea_settings.ikea_settings import IkeaSettings
from comfort.entities.doctype.customer.customer import Customer
from comfort.entities.doctype.item.item import Item
from comfort.integrations.browser_ext import (
    _create_customer,
    _create_sales_order,
    _get_url_to_reference_doc,
    update_token,
)


def test_create_customer_exists_same_name(customer: Customer):
    customer.db_insert()
    doc = _create_customer(customer.name, customer.vk_url)  # type: ignore
    customer.reload()
    assert customer.get_valid_dict() == doc.get_valid_dict()


def test_create_customer_exists_not_same_name(customer: Customer):
    customer.db_insert()
    name = "John Johnson"
    doc = _create_customer(name, customer.vk_url)  # type: ignore
    customer.name = name
    customer.modified = doc.modified
    customer.creation = doc.creation
    assert customer.get_valid_dict() == doc.get_valid_dict()


def test_create_customer_not_exists_not_same_name(customer: Customer):
    doc = _create_customer(customer.name, customer.vk_url)  # type: ignore
    assert doc.name == customer.name
    assert doc.vk_url == customer.vk_url


def test_create_customer_not_exists_same_name(customer: Customer):
    customer.db_insert()
    vk_url = "https://vk.com/im?sel=2"
    doc = _create_customer(customer.name, vk_url)
    assert doc.name == f"{customer.name} 2"
    assert doc.vk_url == vk_url


def patch_fetch_items(monkeypatch: pytest.MonkeyPatch):
    def mock_fetch_items(item_codes: list[str], force_update: bool):
        return {"successful": item_codes}

    monkeypatch.setattr(
        comfort.integrations.browser_ext, "fetch_items", mock_fetch_items
    )


def test_create_sales_order_with_items(
    monkeypatch: pytest.MonkeyPatch,
    customer: Customer,
    item_no_children: Item,
    commission_settings: CommissionSettings,
):
    customer.db_insert()
    item_no_children.db_insert()
    commission_settings.insert()
    patch_fetch_items(monkeypatch)

    doc = _create_sales_order(customer.name, [item_no_children.item_code])
    assert doc is not None
    assert doc.customer == customer.name
    assert dict(count_qty(doc.items)) == {item_no_children.item_code: 1}


def test_create_sales_order_no_items():
    assert _create_sales_order("John Johnson", []) is None


# patch Customer object to disable vk info fetching
@pytest.mark.usefixtures("customer")
def test_get_url_to_reference_doc_with_items(
    monkeypatch: pytest.MonkeyPatch,
    item_no_children: Item,
    commission_settings: CommissionSettings,
):
    item_no_children.db_insert()
    commission_settings.insert()
    patch_fetch_items(monkeypatch)

    customer_name = "John Johnson"
    customer = _create_customer(customer_name, "https://vk.com/im?sel=1")
    sales_order = _create_sales_order(customer_name, [item_no_children.item_code])
    assert re.match(
        rf"http://tests:\d+/app/sales-order/SO-{datetime.now().year}-0001",
        _get_url_to_reference_doc(customer, sales_order),
    )


@pytest.mark.usefixtures("customer")
def test_get_url_to_reference_doc_no_items():
    customer_name = "John Johnson"
    customer = _create_customer(customer_name, "https://vk.com/im?sel=1")
    sales_order = _create_sales_order(customer_name, [])
    assert re.match(
        r"http://tests:\d+/app/customer/John%20Johnson",
        _get_url_to_reference_doc(customer, sales_order),
    )


mock_decoded_token = {
    "https://accounts.ikea.com/customerType": "individual",
    "https://accounts.ikea.com/retailUnit": "RU",
    "https://accounts.ikea.com/memberId": "1111111111",
    "https://accounts.ikea.com/partyUId": "111111111111111111111111111",
    "iss": "https://ru.accounts.ikea.com/",
    "sub": "auth0|1111111111",
    "aud": [
        "https://retail.api.ikea.com",
        "https://ikea-prod-ru.eu.auth0.com/userinfo",
    ],
    "iat": 1111111111,
    "exp": 1000000001,  # explicitly don't validate expiration time
    "azp": "11111fsklfjweifiicni190h",
    "scope": "openid profile email",
}


def test_update_token():
    token = PyJWT().encode(mock_decoded_token, "secret")
    assert update_token(token) == {}  # type: ignore
    doc = get_doc(IkeaSettings)
    assert doc.authorized_token == token.decode()
    assert int(doc.authorized_token_expiration) == mock_decoded_token["exp"]  # type: ignore
