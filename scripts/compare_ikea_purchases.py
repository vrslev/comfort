import argparse
import re
import sys
from typing import Any, TypedDict

from ikea_api import IKEA, format_item_code


class FetchedItem(TypedDict):
    item_code: str
    qty: int
    price: int


class MappedItem(TypedDict):
    quantity: int
    price: int


def get_price(item: dict[str, Any]) -> int:
    match = re.findall(r"(.*),\d+", item["unitPrice"]["formatted"])[0]
    return int(re.sub(r"[^\d]+", "", match))


def fetch_items_in_purchase(
    *, ikea: IKEA, email: str, order_number: str
) -> list[FetchedItem]:
    purchase = ikea.purchases.order_info(
        queries=["ProductListOrder"],
        email=email,
        order_number=order_number,
        take_products=10000000,
    )
    raw_items: list[dict[str, Any]] = purchase[0]["data"]["order"]["articles"]["any"]
    return [
        {"item_code": item["id"], "qty": item["quantity"], "price": get_price(item)}
        for item in raw_items
    ]


def get_items_map(items: list[FetchedItem]):
    res: dict[str, MappedItem] = {}
    for item in items:
        item_code = item["item_code"]
        if item_code not in res:
            res[item_code] = {"quantity": 0, "price": item["price"]}
        res[item_code]["quantity"] += item["qty"]
    return res


def compare_items(before: list[FetchedItem], after: list[FetchedItem]):
    map_before = get_items_map(before)
    res: dict[str, tuple[MappedItem, MappedItem]] = {}

    for item_code, item_after in get_items_map(after).items():
        item_before = map_before.get(item_code)
        if item_before and item_after["price"] != item_before["price"]:
            res[item_code] = item_before, item_after
    return res


def print_differences(
    *,
    first_purchase_no: str,
    second_purchase_no: str,
    item_comparison: dict[str, tuple[MappedItem, MappedItem]],
):
    print(f"Сравнение цен в заказах {first_purchase_no} и {second_purchase_no}.\n")

    full_diff = 0
    for item_code, (item_before, item_after) in item_comparison.items():
        diff = (
            item_after["quantity"] * item_after["price"]
            - item_before["quantity"] * item_before["price"]
        )
        full_diff += diff
        print(
            f"{format_item_code(item_code)}. До: {item_before['quantity']} × {item_before['price']} ₽."
            + f" После: {item_after['quantity']} × {item_after['price']} ₽. Разница: {diff} ₽"
        )

    print(f"\nОбщая разница: {full_diff} ₽.")


def fetch_and_compare_orders(
    *, ikea: IKEA, email: str, first_purchase_no: str, second_purchase_no: str
):
    before = fetch_items_in_purchase(
        ikea=ikea, email=email, order_number=first_purchase_no
    )
    after = fetch_items_in_purchase(
        ikea=ikea, email=email, order_number=second_purchase_no
    )
    item_comparison = compare_items(before, after)
    print_differences(
        first_purchase_no=first_purchase_no,
        second_purchase_no=second_purchase_no,
        item_comparison=item_comparison,
    )


def main(_args: list[str]) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("first_purchase_no")
    parser.add_argument("second_purchase_no")
    parser.add_argument("--email", required=True)
    args = parser.parse_args(_args)
    ikea = IKEA()
    ikea.login_as_guest()
    fetch_and_compare_orders(
        ikea=ikea,
        email=args.email,
        first_purchase_no=args.first_purchase_no,
        second_purchase_no=args.second_purchase_no,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
