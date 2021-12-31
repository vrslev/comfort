from __future__ import annotations

from datetime import date
from typing import TypedDict

import ikea_api
import ikea_api.wrappers
import sentry_sdk
from ikea_api import format_item_code as format_item_code  # For jenv hook
from ikea_api.exceptions import (
    GraphQLError,
    IKEAAPIError,
    ItemFetchError,
    NoDeliveryOptionsAvailableError,
    OrderCaptureError,
)
from ikea_api.wrappers import types

import frappe
from comfort import (
    ValidationError,
    _,
    count_qty,
    counters_are_same,
    doc_exists,
    get_all,
    get_cached_value,
    get_doc,
    new_doc,
)
from comfort.comfort_core.doctype.ikea_settings.ikea_settings import (
    get_authorized_api,
    get_guest_api,
)
from comfort.entities.doctype.item.item import Item
from comfort.entities.doctype.item_category.item_category import ItemCategory


def get_delivery_services(items: dict[str, int]):
    if sum(items.values()) == 0:
        raise ValidationError(_("No items selected to check delivery services"))

    api = get_guest_api()
    zip_code: str | None = get_cached_value(
        "Ikea Settings", "Ikea Settings", "zip_code"
    )
    if not zip_code:
        raise ValidationError(_("Enter Zip Code in Ikea Settings"))

    try:
        res = ikea_api.wrappers.get_delivery_services(
            api, items=items, zip_code=zip_code
        )

    except NoDeliveryOptionsAvailableError:
        frappe.msgprint(_("No available delivery options"), alert=True, indicator="red")

    except OrderCaptureError as exc:
        if (
            isinstance(exc.response._json, dict)
            and "message" in exc.response._json
            and isinstance(exc.response._json["message"], str)
            and (
                "Error while connecting to" in exc.response._json["message"]
                or "Cannot read property 'get' of undefined"
                in exc.response._json["message"]
            )
        ):
            return frappe.msgprint(
                _("Internal IKEA error, try again"), alert=True, indicator="red"
            )
        raise

    except IKEAAPIError as exc:
        if exc.response.status_code == 502:
            return frappe.msgprint(
                _("Internal IKEA error, try again"), alert=True, indicator="red"
            )
        raise

    else:
        if not res.delivery_options:
            frappe.msgprint(
                _("No available delivery options"), alert=True, indicator="red"
            )
            return

        return res


def add_items_to_cart(items: dict[str, int], authorize: bool):
    if sum(items.values()) == 0:
        raise ValidationError(_("No items selected to add to cart"))

    api = get_authorized_api() if authorize else get_guest_api()
    ikea_api.wrappers.add_items_to_cart(api, items=items)


@frappe.whitelist()
def get_purchase_history():
    return [
        p.dict() for p in ikea_api.wrappers.get_purchase_history(get_authorized_api())
    ]


class PurchaseInfoDict(TypedDict):
    delivery_cost: float
    total_cost: float
    purchase_date: date | None
    delivery_date: date | None


@frappe.whitelist()
def get_purchase_info(purchase_id: int, use_lite_id: bool) -> PurchaseInfoDict | None:
    api = get_authorized_api()
    id = str(purchase_id)
    email = (
        get_cached_value("Ikea Settings", "Ikea Settings", "username")
        if use_lite_id
        else None
    )

    try:
        for _ in range(3):
            try:
                return ikea_api.wrappers.get_purchase_info(  # type: ignore
                    api=api, id=id, email=email
                ).dict()
            except IKEAAPIError as exc:
                if exc.response.status_code != 504:
                    raise
    except GraphQLError as exc:
        if isinstance(exc.errors, list) and exc.errors:
            exc.errors = exc.errors[0]
        if isinstance(exc.errors, dict):
            exc.errors = [exc.errors]
        for error in exc.errors:
            if "message" not in error:
                continue
            if error["message"] in (
                "Purchase not found",
                "Order not found",
                "Invalid order id",
                "Exception while fetching data (/order/id) : null",
            ):
                return
        sentry_sdk.capture_exception(exc)


def _make_item_category(name: str | None, url: str | None):
    if name and not doc_exists("Item Category", name):
        doc = new_doc(ItemCategory)
        doc.category_name = name
        doc.url = url
        doc.insert()


def _make_items_from_child_items_if_not_exist(parsed_item: types.ParsedItem):
    for child_item in parsed_item.child_items:
        if not doc_exists("Item", child_item.item_code):
            doc = new_doc(Item)
            doc.item_code = child_item.item_code
            doc.item_name = child_item.name
            doc.weight = child_item.weight
            doc.insert()


def _create_item(parsed_item: types.ParsedItem):
    if doc_exists("Item", parsed_item.item_code):
        doc = get_doc(Item, parsed_item.item_code)
        doc.item_name = parsed_item.name
        doc.url = parsed_item.url
        doc.rate = parsed_item.price
        doc.weight = parsed_item.weight
        doc.image = parsed_item.image_url
        if not counters_are_same(
            count_qty(doc.child_items), count_qty(parsed_item.child_items)
        ):
            doc.child_items = []
            doc.extend(
                "child_items",
                [
                    {
                        "item_code": i.item_code,
                        "item_name": i.name,
                        "weight": i.weight,
                        "qty": i.qty,
                    }
                    for i in parsed_item.child_items
                ],
            )
        doc.item_categories = []
        if parsed_item.category_name:
            doc.append("item_categories", {"item_category": parsed_item.category_name})
        doc.save()

    else:
        doc = new_doc(Item)
        doc.item_code = parsed_item.item_code
        doc.item_name = parsed_item.name
        doc.url = parsed_item.url
        doc.rate = parsed_item.price
        doc.weight = parsed_item.weight
        doc.image = parsed_item.image_url
        doc.child_items = []
        doc.extend(
            "child_items",
            [
                {
                    "item_code": i.item_code,
                    "item_name": i.name,
                    "weight": i.weight,
                    "qty": i.qty,
                }
                for i in parsed_item.child_items
            ],
        )
        doc.item_categories = []
        if parsed_item.category_name:
            doc.append("item_categories", {"item_category": parsed_item.category_name})
        doc.insert()


def _get_items_to_fetch(item_codes: str | list[str], force_update: bool):
    parsed_item_codes = ikea_api.parse_item_codes(item_codes)

    if force_update:
        return parsed_item_codes
    else:
        exist: list[str] = [
            item.item_code
            for item in get_all(
                Item, "item_code", {"item_code": ("in", parsed_item_codes)}
            )
        ]
        return [item_code for item_code in parsed_item_codes if item_code not in exist]


def _create_item_categories(items: list[types.ParsedItem]):
    categories: set[tuple[str | None, str | None]] = set()
    for item in items:
        categories.add((item.category_name, item.category_url))
    for category in categories:
        _make_item_category(*category)


def _fetch_child_items(items: list[types.ParsedItem], force_update: bool):
    items_to_fetch: list[str] = []
    for item in items:
        for child in item.child_items:
            items_to_fetch.append(child.item_code)
    return fetch_items(items_to_fetch, force_update=force_update)


class FetchItemsResult(TypedDict):
    unsuccessful: list[str]
    successful: list[str]


def fetch_items(item_codes: str | list[str], force_update: bool):
    items_to_fetch = _get_items_to_fetch(item_codes, force_update)
    if not items_to_fetch:
        return FetchItemsResult(unsuccessful=[], successful=[])

    parsed_items = ikea_api.wrappers.get_items(items_to_fetch)

    _create_item_categories(parsed_items)
    _fetch_child_items(parsed_items, force_update)

    fetched_item_codes: list[str] = []
    for parsed_item in parsed_items:
        _make_items_from_child_items_if_not_exist(parsed_item)
        _create_item(parsed_item)
        fetched_item_codes.append(parsed_item.item_code)

    return FetchItemsResult(
        successful=[i for i in items_to_fetch if i in fetched_item_codes],
        unsuccessful=[i for i in items_to_fetch if i not in fetched_item_codes],
    )


@frappe.whitelist()
def get_items(item_codes: str):  # pragma: no cover
    """Fetch items, show message about unsuccessful ones and retrieve basic information about fetched items."""
    try:
        response = fetch_items(item_codes, force_update=True)
    except ItemFetchError as e:
        if not (
            e.args
            and e.args[0]
            and isinstance(e.args[0], list)
            and isinstance(e.args[0][0], str)
        ):
            raise

        # If error has this format: ItemFetchError(["item_code", ...])
        if unsuccessful := ikea_api.parse_item_codes(e.args[0]):  # type: ignore
            response = FetchItemsResult(unsuccessful=unsuccessful, successful=[])
            sentry_sdk.capture_exception(e)
        else:
            raise

    if response["unsuccessful"]:
        frappe.msgprint(
            _("Cannot fetch those items: {}").format(
                ", ".join(response["unsuccessful"])
            )
        )
    return get_all(
        Item,
        fields=("item_code", "item_name", "rate", "weight"),
        filters={"item_code": ("in", response["successful"])},
    )
