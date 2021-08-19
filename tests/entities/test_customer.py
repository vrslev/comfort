from __future__ import annotations

import pytest

from comfort.entities.doctype.customer.customer import Customer
from frappe import ValidationError

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


@pytest.mark.parametrize("vk_url", acceptable_vk_urls)
def test_validate_vk_url(customer: Customer, vk_url: str | None):
    customer.vk_url = vk_url
    customer.validate_vk_url_and_set_vk_id()


@pytest.mark.parametrize("vk_url,vk_id", zip(acceptable_vk_urls, expected_vk_ids))
def test_set_vk_id(customer: Customer, vk_url: str | None, vk_id: str | None):
    customer.vk_url = vk_url
    customer.validate_vk_url_and_set_vk_id()
    assert customer.vk_id == vk_id


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
def test_validate_vk_url_and_set_vk_id_raises_on_wrong_url(
    customer: Customer, vk_url: str
):
    customer.vk_url = vk_url
    with pytest.raises(ValidationError):
        customer.validate_vk_url_and_set_vk_id()
