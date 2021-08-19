from dataclasses import dataclass

import pytest

import comfort
import frappe
from comfort import count_quantity, group_by_key, maybe_json


@dataclass
class MockItem:
    item_code: str
    qty: int


data = [
    MockItem(item_code="1", qty=2),
    MockItem(item_code="1", qty=5),
    MockItem(item_code="2", qty=5),
]


def test_count_quantity():
    expected = (("1", 7), ("2", 5))
    for pair in count_quantity(data).items():
        assert pair in expected


def test_group_by_key():
    expected = (
        ("1", [MockItem(item_code="1", qty=2), MockItem(item_code="1", qty=5)]),
        ("2", [MockItem(item_code="2", qty=5)]),
    )
    for pair in group_by_key(data).items():
        assert pair in expected


def test_maybe_json():
    assert maybe_json("[]") == []
    assert maybe_json([]) == []  # type: ignore
    assert maybe_json("[") == "["


def test_validation_error():
    with pytest.raises(frappe.exceptions.ValidationError):
        raise comfort.ValidationError
