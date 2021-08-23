from unicodedata import category

import pytest
from ikea_api_wrapped.wrappers import AnyParsedItem

import frappe
from comfort.comfort_core.ikea import _make_item_category, add_item
from comfort.entities.doctype.item_category.item_category import ItemCategory


@pytest.fixture
def parsed_item() -> AnyParsedItem:
    return {
        "is_combination": True,
        "item_code": "79305814",
        "name": "ПАКС, Гардероб, 150x66x236 см, белый, Фэрвик белое стекло",
        "image_url": "https://www.ikea.com/ru/ru/images/products/paks-garderob-belyj__0626214_PE702156_S5.JPG",
        "child_items": [
            {
                "item_code": "00443776",
                "item_name": "КОМПЛИМЕНТ, устройство для плавного закрывания, 150x66x236 см, белый, Фэрвик белое стекло",
                "weight": 0.57,
                "qty": 1,
            },
            {
                "item_code": "10366598",
                "item_name": "КОМПЛИМЕНТ, штанга платяная, 150x66x236 см, белый, Фэрвик белое стекло",
                "weight": 0.43,
                "qty": 2,
            },
            {
                "item_code": "10401498",
                "item_name": "КОМПЛИМЕНТ, сетчатая корзина, 150x66x236 см, белый, Фэрвик белое стекло",
                "weight": 1.74,
                "qty": 4,
            },
            {
                "item_code": "20277974",
                "item_name": "КОМПЛИМЕНТ, полка, 150x66x236 см, белый, Фэрвик белое стекло",
                "weight": 4.66,
                "qty": 6,
            },
            {
                "item_code": "20366574",
                "item_name": "ПАКС, рама д/раздв дврц, с направл, 2 шт, 150x66x236 см, белый, Фэрвик белое стекло",
                "weight": 17.2,
                "qty": 1,
            },
            {
                "item_code": "30366644",
                "item_name": "КОМПЛИМЕНТ, направляющие для корзин, 150x66x236 см, белый, Фэрвик белое стекло",
                "weight": 0.44,
                "qty": 4,
            },
            {
                "item_code": "50121575",
                "item_name": "ПАКС, каркас гардероба, 150x66x236 см, белый, Фэрвик белое стекло",
                "weight": 46.8,
                "qty": 2,
            },
            {
                "item_code": "90366561",
                "item_name": "ФЭРВИК, 4 панели д/рамы раздвижной дверцы, 150x66x236 см, белый, Фэрвик белое стекло",
                "weight": 13.05,
                "qty": 2,
            },
        ],
        "weight": 175.01,
        "price": 33000,
        "category_name": "Шкафы-купе",
        "category_url": "https://www.ikea.com/ru/ru/cat/-43635",
        "url": "https://www.ikea.com/ru/ru/p/-s79305814",
    }


def test_add_item(parsed_item: AnyParsedItem):
    _make_item_category(parsed_item["category_name"], parsed_item["category_url"])
    categories: list[ItemCategory] = frappe.get_all(
        "Item Category", ["item_category_name", "url"]
    )
    # raise Exception(res)
    assert categories[0].item_category_name == parsed_item["category_name"]
    assert categories[0].url == parsed_item["category_url"]
    # # raise Exception(parsed_items[0])
    # add_item(parsed_items[0], True)
