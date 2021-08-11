from __future__ import annotations

import pytest

import frappe
from comfort.entities.doctype.item.item import Item
from frappe import ValidationError


# TODO: Two test cases: with item and combination
@pytest.fixture
def child_items() -> list[Item]:
    return [frappe.get_doc(i).insert() for i in test_child_items]


@pytest.fixture
def item() -> Item:
    return frappe.get_doc(test_item)


@pytest.fixture
def item_no_children():
    doc: Item = frappe.get_doc(test_item)
    doc.child_items = []
    return doc


def test_validate_child_items(item: Item, child_items: list[Item]):
    item.validate_child_items()

    frappe.get_doc(
        {
            "doctype": "Child Item",
            "item_code": child_items[0].item_code,
            "item_name": child_items[0].item_name,
            "qty": 2,
            "parenttype": "Item",
            "parent": child_items[1].item_code,  # this causes ValidationError
        }
    ).insert()
    with pytest.raises(
        ValidationError, match="Can't add child item that contains child items"
    ):
        item.validate_child_items()


def test_validate_url(item: Item):  # TODO: Parametrize
    item.validate_url()

    item.url = "https://example.com/f023"
    with pytest.raises(ValidationError, match="Invalid URL"):
        item.validate_url()


def test_set_name(item: Item):
    item.set_name()
    assert item.item_name != item.item_code

    item.item_name = None
    item.set_name()
    assert item.item_name == item.item_code


def test_calculate_weight(item: Item, child_items: list[Item]):
    item.calculate_weight()
    assert item.weight == 180.49


def test_calculate_weight_not_executed_when_is_not_combination(item_no_children: Item):
    item_no_children.weight = 10
    item_no_children.calculate_weight()
    assert item_no_children.weight == 10


def test_calculate_weight_in_parent_docs(item: Item, child_items: list[Item]):
    item.calculate_weight()
    item.insert()

    child_items[0].weight += 10
    child_items[0].calculate_weight_in_parent_docs()
    child_items[0].save()

    child_item_qty: int = frappe.db.get_value(
        "Child Item",
        {"parent": item.item_code, "item_code": child_items[0].item_code},
        "qty",
    )
    expected_weight = item.weight + child_item_qty * 10

    new_weight: float = frappe.db.get_value("Item", item.item_code, "weight")
    assert expected_weight == new_weight


def test_create_bin_not_created_for_combination(item: Item):
    item.create_bin()
    assert not frappe.db.exists("Bin", item.item_code)


def test_create_bin_created_for_items_in_combinations(
    item: Item, child_items: list[Item]
):
    item.insert()
    for c in item.child_items:
        assert frappe.db.exists("Bin", c.item_code)


def test_create_bin_created_for_not_combination(item_no_children: Item):
    item_no_children.insert()  # .create_bin() should be called in after_insert hook
    assert frappe.db.exists("Bin", item_no_children.item_code)


def test_delete_bin(item_no_children: Item):
    # .delete_bin() is being called only if no child items
    item_no_children.insert()
    item_no_children.delete_bin()
    assert not frappe.db.exists("Bin", item_no_children.item_code)


def test_delete_bin_raises_if_bin_is_not_empty(item_no_children: Item):
    item_no_children.insert()
    bin = frappe.get_doc("Bin", item_no_children.item_code)
    bin.reserved_actual = 1
    bin.save()
    with pytest.raises(
        ValidationError, match="Can't delete item that have been used in transactions"
    ):
        item_no_children.delete_bin()


test_item = {
    "item_code": "29128569",
    "item_name": "ПАКС Гардероб, 175x58x236 см, белый",
    "url": "https://www.ikea.com/ru/ru/p/-s29128569",
    "rate": 17950,
    "doctype": "Item",
    "child_items": [
        {
            "item_code": "10014030",
            "item_name": "ПАКС Каркас гардероба, 50x58x236 см, белый",
            "qty": 2,
        },
        {
            "item_code": "10366598",
            "item_name": "КОМПЛИМЕНТ Штанга платяная, 75 см, белый",
            "qty": 1,
        },
        {
            "item_code": "20277974",
            "item_name": "КОМПЛИМЕНТ Полка, 75x58 см, белый",
            "qty": 2,
        },
        {
            "item_code": "40277973",
            "item_name": "КОМПЛИМЕНТ Полка, 50x58 см, белый",
            "qty": 6,
        },
        {
            "item_code": "40366634",
            "item_name": "КОМПЛИМЕНТ Ящик, 75x58 см, белый",
            "qty": 3,
        },
        {
            "item_code": "50121575",
            "item_name": "ПАКС Каркас гардероба, 75x58x236 см, белый",
            "qty": 1,
        },
        {
            "item_code": "50366596",
            "item_name": "КОМПЛИМЕНТ Штанга платяная, 50 см, белый",
            "qty": 1,
        },
    ],
}

test_child_items = [
    {
        "item_code": "10014030",
        "item_name": "ПАКС Каркас гардероба, 50x58x236 см, белый",
        "url": "https://www.ikea.com/ru/ru/p/-10014030",
        "rate": 3100,
        "weight": 41.3,
        "doctype": "Item",
        "child_items": [],
    },
    {
        "item_code": "10366598",
        "item_name": "КОМПЛИМЕНТ Штанга платяная, 75 см, белый",
        "url": "https://www.ikea.com/ru/ru/p/-10366598",
        "rate": 250,
        "weight": 0.43,
        "doctype": "Item",
    },
    {
        "item_code": "20277974",
        "item_name": "КОМПЛИМЕНТ Полка, 75x58 см, белый",
        "url": "https://www.ikea.com/ru/ru/p/-20277974",
        "rate": 400,
        "weight": 4.66,
        "doctype": "Item",
    },
    {
        "item_code": "40277973",
        "item_name": "КОМПЛИМЕНТ Полка, 50x58 см, белый",
        "url": "https://www.ikea.com/ru/ru/p/-40277973",
        "rate": 300,
        "weight": 2.98,
        "doctype": "Item",
    },
    {
        "item_code": "40366634",
        "item_name": "КОМПЛИМЕНТ Ящик, 75x58 см, белый",
        "url": "https://www.ikea.com/ru/ru/p/-40366634",
        "rate": 1700,
        "weight": 7.72,
        "doctype": "Item",
    },
    {
        "item_code": "50121575",
        "item_name": "ПАКС Каркас гардероба, 75x58x236 см, белый",
        "url": "https://www.ikea.com/ru/ru/p/-50121575",
        "rate": 3600,
        "weight": 46.8,
        "doctype": "Item",
    },
    {
        "item_code": "50366596",
        "item_name": "КОМПЛИМЕНТ Штанга платяная, 50 см, белый",
        "url": "https://www.ikea.com/ru/ru/p/-50366596",
        "rate": 200,
        "weight": 0.3,
        "doctype": "Item",
    },
]
