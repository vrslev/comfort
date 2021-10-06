import pytest

import comfort.integrations.browser_ext
from comfort import count_qty, new_doc
from comfort.comfort_core.doctype.commission_settings.commission_settings import (
    CommissionSettings,
)
from comfort.entities.doctype.customer.customer import Customer
from comfort.entities.doctype.item.item import Item
from comfort.integrations.browser_ext import (
    _create_customer,
    _create_sales_order,
    _generate_new_customer_name,
    _get_url_to_reference_doc,
)


def test_generate_new_customer_name_not_exists():
    name = "John Johnson"
    assert _generate_new_customer_name(name) == name


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
def test_generate_new_customer_name_exists(input: str, exp_output: str):
    doc = new_doc(Customer)
    doc.name = input
    doc.db_insert()

    assert _generate_new_customer_name(input) == exp_output


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
    assert (
        _get_url_to_reference_doc(customer, sales_order)
        == "http://tests:8005/app/sales-order/SO-2021-0001"
    )


def test_get_url_to_reference_doc_no_items():
    customer_name = "John Johnson"
    customer = _create_customer(customer_name, "https://vk.com/im?sel=1")
    sales_order = _create_sales_order(customer_name, [])
    assert (
        _get_url_to_reference_doc(customer, sales_order)
        == "http://tests:8005/app/customer/John%20Johnson"
    )
