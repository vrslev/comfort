import random
from typing import TYPE_CHECKING

import pytest

import frappe
from comfort.entities.doctype.item.item import Item
from comfort.stock.doctype.bin.bin import Bin

if not TYPE_CHECKING:
    from tests.entities.test_item import item_no_children


@pytest.fixture
def bin(item_no_children: Item) -> Bin:
    item_no_children.db_insert()
    return frappe.get_doc(
        {
            "item_code": item_no_children.item_code,
            "doctype": "Bin",
        }
    )


def test_fill_with_nulls(bin: Bin):
    bin.fill_with_nulls()
    assert bin.reserved_actual == 0
    assert bin.available_actual == 0
    assert bin.reserved_purchased == 0
    assert bin.available_purchased == 0


def test_calculate_projected(bin: Bin):
    bin.reserved_actual = 1
    bin.available_actual = 0
    bin.reserved_purchased = 3
    bin.available_purchased = 10
    bin.calculate_projected()
    assert bin.projected == 6


@pytest.mark.parametrize("value,expected", ((0, True), (10, False)))
def test_is_empty_property(bin: Bin, value: int, expected: bool):
    bin.fill_with_nulls()
    bin_fields = [
        "reserved_actual",
        "available_actual",
        "reserved_purchased",
        "available_purchased",
    ]
    field = bin_fields[random.randrange(len(bin_fields))]  # nosec

    setattr(bin, field, value)
    assert bin.is_empty == expected


def test_update_for(bin: Bin):
    bin.db_insert()
    bin.update_for(bin.item_code, reserved_actual=100)
    bin.reload()
    assert bin.reserved_actual == 100
