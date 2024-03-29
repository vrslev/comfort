from __future__ import annotations

import pytest

from comfort.entities.doctype.item_category.item_category import ItemCategory
from frappe import ValidationError


@pytest.mark.parametrize(
    "url",
    (
        "ikea.com/ru/ru/cat/-11844",
        "www.ikea.com/ru/ru/cat/-11844",
        "https://www.ikea.com/ru/ru/cat/-11844",
        "https://www.ikea.com/ru/ru/cat/-154",
        "https://www.ikea.com/us/en/cat/-11844",
        "https://www.ikea.com/ru/ru/cat/komplekty-postelnogo-belya-10680/",
        None,
    ),
)
def test_item_category_validate(item_category: ItemCategory, url: str | None):
    item_category.url = url
    item_category.validate()


@pytest.mark.parametrize(
    "url",
    (
        "ikea.com",
        "https://ikea.com/cat/-11844",
        "https://ikea.com/ru/cat/-11844",
        "https://ikea.com/ru/ru/category/-11844",
        "https://ikea.com/category/-11844",
        "https://example.com/category/-11844",
    ),
)
def test_item_category_validate_raises_on_wrong_url(
    item_category: ItemCategory, url: str | None
):
    item_category.url = url
    with pytest.raises(ValidationError, match="Invalid category URL"):
        item_category.validate()
