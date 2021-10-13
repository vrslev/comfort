import pytest

import comfort.comfort_core
from comfort.comfort_core import get_items
from comfort.entities.doctype.item.item import Item
from comfort.integrations.ikea import FetchItemsResult


def test_get_items_success(monkeypatch: pytest.MonkeyPatch, item_no_children: Item):
    def mock_fetch_items(item_codes: str, force_update: bool):
        assert force_update
        return FetchItemsResult(unsuccessful=[], successful=[item_codes])

    monkeypatch.setattr(comfort.comfort_core, "fetch_items", mock_fetch_items)
    item_no_children.db_insert()

    res = get_items(item_codes=item_no_children.item_code)[0]
    assert res.item_code == item_no_children.item_code
    assert res.item_name == item_no_children.item_name
    assert res.rate == item_no_children.rate
    assert res.weight == 0.0


def test_get_items_failure(monkeypatch: pytest.MonkeyPatch):
    mock_item_codes = ["2131418", "147126876"]

    def mock_fetch_items(item_codes: str, force_update: bool):
        assert force_update
        return FetchItemsResult(unsuccessful=mock_item_codes, successful=[])

    monkeypatch.setattr(comfort.comfort_core, "fetch_items", mock_fetch_items)

    get_items(item_codes="81042840")
    import frappe

    assert f"Cannot fetch those items: {', '.join(mock_item_codes)}" in str(
        frappe.message_log  # type: ignore
    )
