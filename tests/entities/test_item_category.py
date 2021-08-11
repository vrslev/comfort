from __future__ import annotations

import pytest

import frappe
from comfort.entities.doctype.item_category.item_category import ItemCategory
from frappe import ValidationError


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


@pytest.mark.parametrize(
    "url",
    (
        "ikea.com/ru/ru/cat/-11844",
        "www.ikea.com/ru/ru/cat/-11844",
        "https://www.ikea.com/ru/ru/cat/-11844",
        "https://www.ikea.com/ru/ru/cat/-154",
        "https://www.ikea.com/us/en/cat/-11844",
        None,
    ),
)
def test_validate_url(item_category: ItemCategory, url: str | None):
    item_category.url = url
    item_category.validate_url()


@pytest.mark.parametrize(
    "url",
    (
        "ikea.com",
        "https://ikea.com/cat/-11844",
        "https://ikea.com/ru/cat/-11844",
        "https://www.ikea.com/ru/ru/cat/",
        "https://www.ikea.com/ru/ru/cat/11844",
        "https://www.ikea.com/ru/ru/cat/-sometext",
        "https://ikea.com/ru/ru/category/-11844",
        "https://ikea.com/category/-11844",
        "https://example.com/category/-11844",
    ),
)
def test_validate_url_raises_on_wrong_url(item_category: ItemCategory, url: str | None):
    item_category.url = url
    with pytest.raises(ValidationError, match="Invalid category URL"):
        item_category.validate_url()
