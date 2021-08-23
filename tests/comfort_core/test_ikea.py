import pytest
from ikea_api_wrapped.parsers.item import ParsedItem

import frappe
from comfort import count_quantity, counters_are_same
from comfort.comfort_core.ikea import (
    _child_items_are_same,
    _create_item,
    _create_item_categories,
    _get_items_to_fetch,
    _make_item_category,
    _make_items_from_child_items_if_not_exist,
)
from comfort.entities.doctype.item.item import Item
from comfort.entities.doctype.item_category.item_category import ItemCategory


@pytest.fixture
def parsed_item() -> ParsedItem:
    return {
        "is_combination": True,
        "item_code": "29128569",
        "name": "ПАКС, Гардероб, 175x58x236 см, белый",
        "image_url": "https://www.ikea.com/ru/ru/images/products/paks-garderob-belyj__0383288_PE557277_S5.JPG",
        "weight": 0.0,
        "child_items": [
            {
                "item_code": "10014030",
                "item_name": "ПАКС, Каркас гардероба, 175x58x236 см, белый",
                "weight": 41.3,
                "qty": 2,
            },
            {
                "item_code": "10366598",
                "item_name": "КОМПЛИМЕНТ, Штанга платяная, 175x58x236 см, белый",
                "weight": 0.43,
                "qty": 1,
            },
            {
                "item_code": "20277974",
                "item_name": "КОМПЛИМЕНТ, Полка, 175x58x236 см, белый",
                "weight": 4.66,
                "qty": 2,
            },
            {
                "item_code": "40277973",
                "item_name": "КОМПЛИМЕНТ, Полка, 175x58x236 см, белый",
                "weight": 2.98,
                "qty": 6,
            },
            {
                "item_code": "40366634",
                "item_name": "КОМПЛИМЕНТ, Ящик, 175x58x236 см, белый",
                "weight": 7.72,
                "qty": 3,
            },
            {
                "item_code": "50121575",
                "item_name": "ПАКС, Каркас гардероба, 175x58x236 см, белый",
                "weight": 46.8,
                "qty": 1,
            },
            {
                "item_code": "50366596",
                "item_name": "КОМПЛИМЕНТ, Штанга платяная, 175x58x236 см, белый",
                "weight": 0.3,
                "qty": 1,
            },
        ],
        "price": 17950,
        "url": "https://www.ikea.com/ru/ru/p/-s29128569",
        "category_name": "Открытые гардеробы",
        "category_url": "https://www.ikea.com/ru/ru/cat/-43634",
    }


def test_make_item_category_not_exists(parsed_item: ParsedItem):
    _make_item_category(parsed_item["category_name"], parsed_item["category_url"])
    categories: list[ItemCategory] = frappe.get_all(
        "Item Category", ["category_name", "url"]
    )
    assert categories[0].category_name == parsed_item["category_name"]
    assert categories[0].url == parsed_item["category_url"]


def test_make_item_category_exists(parsed_item: ParsedItem):
    _make_item_category(parsed_item["category_name"], parsed_item["category_url"])
    _make_item_category(
        parsed_item["category_name"], "https://www.ikea.com/ru/ru/cat/-43638"
    )
    categories: list[ItemCategory] = frappe.get_all("Item Category", "url")
    assert categories[0].url == parsed_item["category_url"]


def test_make_items_from_child_items_if_not_exist(parsed_item: ParsedItem):
    _make_items_from_child_items_if_not_exist(parsed_item)
    assert (
        len(
            {item["item_code"] for item in parsed_item["child_items"]}  # type: ignore
            ^ {item.item_code for item in frappe.get_all("Item", "item_code")}
        )
        == 0
    )
    _make_items_from_child_items_if_not_exist(parsed_item)  # test if not exists block
    assert (
        len(
            {item["item_code"] for item in parsed_item["child_items"]}  # type: ignore
            ^ {item.item_code for item in frappe.get_all("Item", "item_code")}
        )
        == 0
    )


def test_child_items_are_same_true(item: Item, parsed_item: ParsedItem):
    assert _child_items_are_same(item.child_items, parsed_item["child_items"])


def test_child_items_are_same_false(item: Item, parsed_item: ParsedItem):
    parsed_item["child_items"][0]["qty"] = 1204
    assert not _child_items_are_same(item.child_items, parsed_item["child_items"])


def test_create_item_exists(parsed_item: ParsedItem):
    _make_item_category(parsed_item["category_name"], parsed_item["category_url"])
    _create_item(parsed_item)

    parsed_item["name"] = "My New Fancy Item Name"
    parsed_item["url"] = "https://www.ikea.com/ru/ru/p/-s29128563"
    parsed_item["price"] = 10000253
    parsed_item["category_name"] = "New category"
    _make_item_category(parsed_item["category_name"], parsed_item["category_url"])
    _create_item(parsed_item)

    doc: Item = frappe.get_doc("Item", parsed_item["item_code"])

    assert doc.item_code == parsed_item["item_code"]
    assert doc.item_name == parsed_item["name"]
    assert doc.url == parsed_item["url"]
    assert doc.rate == parsed_item["price"]
    assert counters_are_same(
        count_quantity(doc.child_items),
        count_quantity(
            frappe._dict(item_code=i["item_code"], qty=i["qty"])
            for i in parsed_item["child_items"]
        ),
    )
    assert len(doc.item_categories) == 1
    assert doc.item_categories[0].item_category == parsed_item["category_name"]


def test_create_item_exists_child_items_changed(parsed_item: ParsedItem):
    _make_item_category(parsed_item["category_name"], parsed_item["category_url"])
    _create_item(parsed_item)

    parsed_item["child_items"].pop()
    _create_item(parsed_item)

    doc: Item = frappe.get_doc("Item", parsed_item["item_code"])
    assert counters_are_same(
        count_quantity(doc.child_items),
        count_quantity(
            frappe._dict(item_code=i["item_code"], qty=i["qty"])
            for i in parsed_item["child_items"]
        ),
    )


def test_create_item_not_exists(parsed_item: ParsedItem):
    _make_item_category(parsed_item["category_name"], parsed_item["category_url"])
    _create_item(parsed_item)
    doc: Item = frappe.get_doc("Item", parsed_item["item_code"])

    assert doc.item_code == parsed_item["item_code"]
    assert doc.item_name == parsed_item["name"]
    assert doc.url == parsed_item["url"]
    assert doc.rate == parsed_item["price"]
    assert doc.weight == parsed_item["weight"]
    assert counters_are_same(
        count_quantity(doc.child_items),
        count_quantity(
            frappe._dict(item_code=i["item_code"], qty=i["qty"])
            for i in parsed_item["child_items"]
        ),
    )
    assert len(doc.item_categories) == 1
    assert doc.item_categories[0].item_category == parsed_item["category_name"]


def test_create_item_not_exists_no_child_items(parsed_item: ParsedItem):
    parsed_item["child_items"] = []
    _make_item_category(parsed_item["category_name"], parsed_item["category_url"])
    _create_item(parsed_item)
    doc: Item = frappe.get_doc("Item", parsed_item["item_code"])

    assert len(doc.child_items) == 0


def test_create_item_not_exists_no_item_category(parsed_item: ParsedItem):
    parsed_item["category_name"] = ""
    _create_item(parsed_item)
    doc: Item = frappe.get_doc("Item", parsed_item["item_code"])

    assert len(doc.item_categories) == 0


def test_get_items_to_fetch_force_update():
    item_codes = ["10014030"]
    res = _get_items_to_fetch(item_codes, force_update=True)
    assert len(res) == 1


def test_get_items_to_fetch_not_force_update(item: Item):
    item.db_insert()
    item_codes = [item.item_code]
    res = _get_items_to_fetch(item_codes, force_update=False)
    assert len(res) == 0


def test_create_item_categories(parsed_item: ParsedItem):
    items = [parsed_item, parsed_item.copy(), parsed_item]
    new_category = "New Category Name"
    items[1]["category_name"] = new_category
    _create_item_categories(items)
    assert (
        len(
            {new_category, parsed_item["category_name"]}  # type: ignore
            ^ {c.name for c in frappe.get_all("Item Category")}
        )
        == 0
    )
