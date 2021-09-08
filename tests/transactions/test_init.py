from collections import Counter

import pytest

import frappe
from comfort import count_qty, group_by_attr
from comfort.transactions import delete_empty_items, merge_same_items
from comfort.transactions.doctype.sales_order.sales_order import SalesOrder
from comfort.transactions.doctype.sales_return.sales_return import SalesReturn


def test_return_delete_empty_items(sales_return: SalesReturn):
    sales_return.append("items", {"qty": 0})
    sales_return.delete_empty_items()
    c: Counter[str] = Counter()
    for i in sales_return.items:
        c[i.item_code] += i.qty
    for qty in c.values():
        assert qty > 0


def test_return_delete_empty_items_no_attr(sales_return: SalesReturn):
    del sales_return.items
    sales_return.delete_empty_items()


def test_return_delete_empty_items_attr_is_none(sales_return: SalesReturn):
    sales_return.items = None
    sales_return.delete_empty_items()


def test_return_calculate_item_values(sales_return: SalesReturn):
    sales_return._calculate_item_values()
    for item in sales_return.items:
        assert item.amount == item.qty * item.rate


def test_return_get_remaining_qtys(sales_return: SalesReturn):
    items_in_order = sales_return._voucher._get_items_with_splitted_combinations()
    in_order = count_qty(items_in_order)
    in_return = count_qty(sales_return.items)

    for item_code, qty in sales_return._get_remaining_qtys(items_in_order):
        assert qty > 0
        if qty > 0:
            assert qty == in_order[item_code] - in_return.get(item_code, 0)


def test_return_get_items_available_to_add(sales_return: SalesReturn):
    available_item_and_qty = dict(
        sales_return._get_remaining_qtys(
            sales_return._voucher._get_items_with_splitted_combinations()
        )
    )
    for item in sales_return.get_items_available_to_add():
        assert (item["item_name"], item["rate"]) == frappe.get_value(
            "Item", item["item_code"], ("item_name", "rate")
        )
        assert item["qty"] == available_item_and_qty[item["item_code"]]


@pytest.mark.parametrize(
    ("item_code", "qty"),
    (("invalid_item_code", 10), ("40366634", 0), ("40366634", 3)),
)
def test_return_add_items_raises_on_invalid_item(
    sales_return: SalesReturn, item_code: str, qty: int
):
    all_items = sales_return.get_items_available_to_add()
    counter = count_qty(frappe._dict(d) for d in all_items)

    with pytest.raises(
        frappe.ValidationError,
        match=f"Insufficient quantity {qty} for Item {item_code}: expected not "
        + f"more than {counter.get(item_code, 0)}.",
    ):
        sales_return.add_items(
            [
                {
                    "item_code": item_code,
                    "item_name": "random_name",
                    "qty": qty,
                    "rate": 1000,
                }
            ]
        )


def test_return_add_items_not_raises(sales_return: SalesReturn):
    expected_item_amount = 2000
    test_item = {
        "item_code": "40366634",
        "item_name": "random_name",
        "qty": 2,
        "rate": 1000,
    }
    sales_return.add_items([test_item])

    item_added, item_amount = False, 0
    for item in sales_return.items:
        if {
            "item_code": item.item_code,
            "item_name": item.item_name,
            "qty": item.qty,
            "rate": item.rate,
        } == test_item:
            item_added = True
            item_amount = item.amount

    assert item_added
    assert item_amount == expected_item_amount


def test_return_add_missing_fields_to_items(
    sales_return: SalesReturn, sales_order: SalesOrder
):
    grouped_order_items = group_by_attr(sales_order.items, attr="name")
    items = sales_order._get_items_with_splitted_combinations()
    sales_return._add_missing_fields_to_items(items)

    for item in items:
        if item.doctype == "Sales Order Item":
            assert item.rate == grouped_order_items[item.name][0].rate
        elif item.doctype == "Sales Order Child Item":
            assert item.rate == frappe.get_value("Item", item.item_code, "rate")


def test_return_validate_not_all_items_returned_not_raises(sales_return: SalesReturn):
    sales_return._validate_not_all_items_returned()


def test_return_validate_not_all_items_returned_raises(sales_return: SalesReturn):
    sales_return.add_items(sales_return.get_items_available_to_add())
    with pytest.raises(frappe.ValidationError, match="Can't return all items"):
        sales_return._validate_not_all_items_returned()


def test_return_before_cancel(sales_return: SalesReturn):
    with pytest.raises(frappe.ValidationError, match="Not allowed to cancel Return"):
        sales_return.before_cancel()


def test_delete_empty_items(sales_order: SalesOrder):
    sales_order.append("items", {"qty": 0})
    delete_empty_items(sales_order, "items")

    c: Counter[str] = Counter()
    for i in sales_order.items:
        c[i.item_code] += i.qty

    for qty in c.values():
        assert qty > 0


def test_merge_same_items(sales_order: SalesOrder):
    # TODO: test not messed up
    # TODO
    # @@ -49,7 +49,7 @@
    # -            if len(cur_items) > 1:
    # +            if len(cur_items) >= 1:
    # +            if len(cur_items) > 2:
    # -                full_qty = list(count_quantity(cur_items).values())[0]
    # +                full_qty = None
    # -                cur_items[0].qty = full_qty
    # +                cur_items[1].qty = full_qty
    # +                cur_items[1].qty = None

    item = sales_order.items[0].as_dict().copy()
    item.qty = 4
    second_item = sales_order.items[1].as_dict().copy()
    second_item.qty = 2
    sales_order.extend("items", [item, second_item])

    sales_order.items = merge_same_items(sales_order.items)
    c: Counter[str] = Counter()
    for item in sales_order.items:
        c[item.item_code] += 1

    assert len(sales_order.items) == 2
    assert all(c == 1 for c in c.values())
