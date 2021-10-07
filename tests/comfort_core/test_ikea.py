from types import SimpleNamespace

from ikea_api_wrapped.types import ParsedItem

from comfort import count_qty, counters_are_same, get_all, get_doc
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


def test_make_item_category_not_exists(parsed_item: ParsedItem):
    _make_item_category(parsed_item["category_name"], parsed_item["category_url"])
    categories = get_all(ItemCategory, ("category_name", "url"))
    assert categories[0].category_name == parsed_item["category_name"]
    assert categories[0].url == parsed_item["category_url"]


def test_make_item_category_exists(parsed_item: ParsedItem):
    _make_item_category(parsed_item["category_name"], parsed_item["category_url"])
    _make_item_category(
        parsed_item["category_name"], "https://www.ikea.com/ru/ru/cat/-43638"
    )
    categories = get_all(ItemCategory, "url")
    assert categories[0].url == parsed_item["category_url"]


def test_make_item_category_no_name(parsed_item: ParsedItem):
    _make_item_category(None, parsed_item["category_url"])
    categories = get_all(ItemCategory, "url")
    assert len(categories) == 0


def test_make_items_from_child_items_if_not_exist(parsed_item: ParsedItem):
    _make_items_from_child_items_if_not_exist(parsed_item)
    items_in_db = {item.item_code for item in get_all(Item, "item_code")}
    assert (
        len({item["item_code"] for item in parsed_item["child_items"]} ^ items_in_db)
        == 0
    )
    _make_items_from_child_items_if_not_exist(parsed_item)  # test if not exists block
    items_in_db = {item.item_code for item in get_all(Item, "item_code")}
    assert (
        len({item["item_code"] for item in parsed_item["child_items"]} ^ items_in_db)
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

    doc = get_doc(Item, parsed_item["item_code"])

    assert doc.item_code == parsed_item["item_code"]
    assert doc.item_name == parsed_item["name"]
    assert doc.url == parsed_item["url"]
    assert doc.rate == parsed_item["price"]
    assert counters_are_same(
        count_qty(doc.child_items),
        count_qty(
            SimpleNamespace(item_code=i["item_code"], qty=i["qty"])
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

    doc = get_doc(Item, parsed_item["item_code"])
    assert counters_are_same(
        count_qty(doc.child_items),
        count_qty(
            SimpleNamespace(item_code=i["item_code"], qty=i["qty"])
            for i in parsed_item["child_items"]
        ),
    )


def test_create_item_not_exists(parsed_item: ParsedItem):
    _make_item_category(parsed_item["category_name"], parsed_item["category_url"])
    _create_item(parsed_item)
    doc = get_doc(Item, parsed_item["item_code"])

    assert doc.item_code == parsed_item["item_code"]
    assert doc.item_name == parsed_item["name"]
    assert doc.url == parsed_item["url"]
    assert doc.rate == parsed_item["price"]
    assert doc.weight == parsed_item["weight"]
    assert counters_are_same(
        count_qty(doc.child_items),
        count_qty(
            SimpleNamespace(item_code=i["item_code"], qty=i["qty"])
            for i in parsed_item["child_items"]
        ),
    )
    assert len(doc.item_categories) == 1
    assert doc.item_categories[0].item_category == parsed_item["category_name"]


def test_create_item_not_exists_no_child_items(parsed_item: ParsedItem):
    parsed_item["child_items"] = []
    _make_item_category(parsed_item["category_name"], parsed_item["category_url"])
    _create_item(parsed_item)
    doc = get_doc(Item, parsed_item["item_code"])

    assert len(doc.child_items) == 0


def test_create_item_not_exists_no_item_category(parsed_item: ParsedItem):
    parsed_item["category_name"] = ""
    _create_item(parsed_item)
    doc = get_doc(Item, parsed_item["item_code"])

    assert len(doc.item_categories) == 0


def test_get_items_to_fetch_force_update():
    res = _get_items_to_fetch(["10014030"], force_update=True)
    assert len(res) == 1


def test_get_items_to_fetch_not_force_update(item: Item):
    item.db_insert()
    res = _get_items_to_fetch([item.item_code], force_update=False)
    assert len(res) == 0


def test_create_item_categories(parsed_item: ParsedItem):
    items = [parsed_item, parsed_item.copy(), parsed_item]
    new_category = "New Category Name"
    items[1]["category_name"] = new_category
    _create_item_categories(items)
    categories_in_db = {c.name for c in get_all(ItemCategory)}
    assert len({new_category, parsed_item["category_name"]} ^ categories_in_db) == 0


# TODO: Test and make translatable
# -        frappe.msgprint("Нет доступных способов доставки", alert=True, indicator="red")
# +        frappe.msgprint("Нет доступных способов доставки", alert=False, indicator="red")

# TODO: Test adding item properly
