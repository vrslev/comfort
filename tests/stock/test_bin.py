import random
from typing import TYPE_CHECKING

import pytest

import frappe
from comfort.entities.doctype.item.item import Item
from comfort.stock.doctype.bin.bin import BIN_FIELDS, Bin

if not TYPE_CHECKING:
    from tests.entities.test_item import item_no_children


@pytest.fixture
def bin(item_no_children: Item) -> Bin:
    item_no_children.insert()
    if not frappe.db.exists("Bin", item_no_children.item_code):
        doc = frappe.get_doc(
            {
                "item_code": item_no_children.item_code,
                "doctype": "Bin",
            }
        )
        doc.save()
    else:
        doc = frappe.get_doc("Bin", item_no_children.item_code)
    return doc


def test_fill_with_nulls(bin: Bin):
    item_code = bin.item_code
    bin.delete()
    doc: Bin = frappe.get_doc({"doctype": "Bin", "item_code": item_code})
    doc.fill_with_nulls()

    for f in BIN_FIELDS:
        assert getattr(doc, f) == 0


@pytest.mark.parametrize("value,expected", ((0, True), (10, False)))
def test_is_empty(bin: Bin, value: int, expected: bool):
    field = BIN_FIELDS[random.randrange(len(BIN_FIELDS))]  # nosec
    setattr(bin, field, value)
    assert bin.is_empty == expected
