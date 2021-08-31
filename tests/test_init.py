from dataclasses import dataclass

import pytest

import comfort
import frappe
from comfort import are_same_counters, count_quantity, group_by_attr, maybe_json


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


def test_are_same_counters_true():
    second_data = [
        MockItem(item_code="2", qty=5),
        MockItem(item_code="1", qty=4),
        MockItem(item_code="1", qty=3),
    ]
    assert are_same_counters(count_quantity(data), count_quantity(second_data))


def test_are_same_counters_not_true():
    second_data = [
        MockItem(item_code="2", qty=5),
        MockItem(item_code="1", qty=20),
        MockItem(item_code="1", qty=3),
        MockItem(item_code="3", qty=1),
    ]
    assert not are_same_counters(count_quantity(data), count_quantity(second_data))


def test_group_by_attr():
    expected = (
        ("1", [MockItem(item_code="1", qty=2), MockItem(item_code="1", qty=5)]),
        ("2", [MockItem(item_code="2", qty=5)]),
    )
    for pair in group_by_attr(data).items():
        assert pair in expected


def test_maybe_json():
    assert maybe_json("[]") == []
    assert maybe_json([]) == []  # type: ignore
    assert maybe_json("[") == "["


def test_validation_error():
    with pytest.raises(frappe.exceptions.ValidationError):
        raise comfort.ValidationError
