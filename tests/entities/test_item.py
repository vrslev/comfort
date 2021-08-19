import pytest

import frappe
from comfort.entities.doctype.item.item import Item
from frappe import ValidationError

# TODO: Refactor to make it more "UNIT"
# TODO: Two test cases: with item and combination


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

    child_item_qty: int = frappe.get_value(
        "Child Item",
        {"parent": item.item_code, "item_code": child_items[0].item_code},
        "qty",
    )
    expected_weight = item.weight + child_item_qty * 10

    new_weight: float = frappe.get_value("Item", item.item_code, "weight")
    assert expected_weight == new_weight
