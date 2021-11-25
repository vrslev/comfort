import re
from typing import Any

from ikea_api import IKEA
from ikea_api._api import GraphQLResponse

email = ""
token = ""  # nosec


def compare_orders(first_no: str, second_no: str):
    before = get_items_in_order(first_no)
    after = get_items_in_order(second_no)
    comparison = get_items_in_comparison(before, after)
    print_differences(comparison)


def get_items_in_order(order_number: str):
    api = IKEA(token)
    # TODO: Remove this type hint after
    o: list[GraphQLResponse] = api.purchases.order_info(
        queries=["ProductListOrder"],
        email=email,
        order_number=order_number,
        take_products=1000,
    )

    items_raw = o[0]["data"]["order"]["articles"]["any"]
    items: list[dict[str, Any]] = []
    for i in items_raw:
        item = {
            "item_code": i["id"],
            "qty": i["quantity"],
            "price": int(
                re.sub(
                    r"[^\d]+",
                    "",
                    re.findall(r"(.*),\d+", i["unitPrice"]["formatted"])[0],
                )
            ),
        }
        items.append(item)
    return items


def get_map(d: list[Any]):
    m: dict[Any, Any] = {}
    for v in d:
        code = v["item_code"]
        if code not in m:
            m[code] = {"quantity": 0, "price": v["price"]}
        m[code]["quantity"] += v["qty"]
    return m


def get_items_in_comparison(before: list[Any], after: list[Any]):
    map_before = get_map(before)
    map_after = get_map(after)

    comparison: dict[Any, Any] = {}
    for k, v in map_after.items():
        if k in map_before:
            diff: int = v["price"] - map_before[k]["price"]
            if diff > 0:
                comparison[k] = map_before[k], map_after[k]
    return comparison


def print_differences(comparison: dict[Any, Any]):
    differences: list[Any] = []
    for b, a in comparison.values():
        differences.append(a["quantity"] * a["price"] - b["quantity"] * b["price"])

    for k, (b, a) in comparison.items():
        print(
            f"{k}. До: {b['quantity']} x {b['price']} ₽. После: {a['quantity']} x {a['price']} ₽. Разница: {a['quantity'] * a['price'] - b['quantity'] * b['price']} ₽"
        )
    print("Общая сумма:", sum(differences), "₽")
