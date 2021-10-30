from __future__ import annotations

from types import SimpleNamespace
from typing import Any, TypedDict

import ikea_api_wrapped
import sentry_sdk
from ikea_api.errors import ItemFetchError, OrderCaptureError
from ikea_api_wrapped import format_item_code  # type: ignore  # For jenv hook
from ikea_api_wrapped.types import NoDeliveryOptionsAvailableError, ParsedItem

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
from comfort.entities.doctype.child_item.child_item import ChildItem
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
        return ikea_api_wrapped.get_delivery_services(api, items, zip_code)
    except NoDeliveryOptionsAvailableError:
        frappe.msgprint(_("No available delivery options"), alert=True, indicator="red")
    except OrderCaptureError as exc:
        if isinstance(
            exc.args[0], dict
        ) and "Error while connecting to ISOM" in exc.args[0].get("message", ""):
            frappe.msgprint(
                _("Internal IKEA error, try again"), alert=True, indicator="red"
            )
        else:
            raise


def add_items_to_cart(items: dict[str, int], authorize: bool):
    if sum(items.values()) == 0:
        raise ValidationError(_("No items selected to add to cart"))

    api = get_authorized_api() if authorize else get_guest_api()
    ikea_api_wrapped.add_items_to_cart(api, items)


@frappe.whitelist()
def get_purchase_history():
    return ikea_api_wrapped.get_purchase_history(get_authorized_api())


@frappe.whitelist()
def get_purchase_info(purchase_id: int, use_lite_id: bool):
    email: str | None = None
    if use_lite_id:
        email = get_cached_value("Ikea Settings", "Ikea Settings", "username")
    return ikea_api_wrapped.get_purchase_info(get_authorized_api(), purchase_id, email)


def _make_item_category(name: str | None, url: str | None):
    if name and not doc_exists("Item Category", name):
        doc = new_doc(ItemCategory)
        doc.category_name = name
        doc.url = url
        doc.insert()


def _make_items_from_child_items_if_not_exist(parsed_item: ParsedItem):
    for child_item in parsed_item["child_items"]:
        if not doc_exists("Item", child_item["item_code"]):
            doc = new_doc(Item)
            doc.item_code = child_item["item_code"]
            doc.item_name = child_item["item_name"]
            doc.weight = child_item["weight"]
            doc.insert()


def _child_items_are_same(old_child_items: list[ChildItem], new_child_items: list[Any]):
    counted_new_child_items = count_qty(
        SimpleNamespace(item_code=item["item_code"], qty=item["qty"])
        for item in new_child_items
    )
    counted_old_child_items = count_qty(old_child_items)
    return counters_are_same(counted_new_child_items, counted_old_child_items)


def _create_item(parsed_item: ParsedItem):
    if doc_exists("Item", parsed_item["item_code"]):
        doc = get_doc(Item, parsed_item["item_code"])
        doc.item_name = parsed_item["name"]
        doc.url = parsed_item["url"]
        doc.rate = parsed_item["price"]
        doc.weight = parsed_item["weight"]
        doc.image = parsed_item["image_url"]
        if not _child_items_are_same(doc.child_items, parsed_item["child_items"]):
            doc.child_items = []
            doc.extend("child_items", parsed_item["child_items"])
        doc.item_categories = []
        if parsed_item["category_name"]:
            doc.append(
                "item_categories", {"item_category": parsed_item["category_name"]}
            )
        doc.save()

    else:
        doc = new_doc(Item)
        doc.item_code = parsed_item["item_code"]
        doc.item_name = parsed_item["name"]
        doc.url = parsed_item["url"]
        doc.rate = parsed_item["price"]
        doc.weight = parsed_item["weight"]
        doc.image = parsed_item["image_url"]
        doc.child_items = []
        doc.extend("child_items", parsed_item["child_items"])
        doc.item_categories = []
        if parsed_item["category_name"]:
            doc.append(
                "item_categories", {"item_category": parsed_item["category_name"]}
            )
        doc.insert()


def _get_items_to_fetch(item_codes: str | int | list[str], force_update: bool):
    parsed_item_codes = ikea_api_wrapped.parse_item_codes(item_codes)  # type: ignore

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


def _create_item_categories(items: list[ParsedItem]):
    categories: set[tuple[str | None, str | None]] = set()
    for item in items:
        categories.add((item["category_name"], item["category_url"]))
    for category in categories:
        _make_item_category(*category)


def _fetch_child_items(items: list[ParsedItem], force_update: bool):
    items_to_fetch: list[str] = []
    for item in items:
        for child in item["child_items"]:
            items_to_fetch.append(child["item_code"])
    return fetch_items(items_to_fetch, force_update=force_update)


class FetchItemsResult(TypedDict):
    unsuccessful: list[str]
    successful: list[str]


def fetch_items(item_codes: str | int | list[str], force_update: bool):
    items_to_fetch = _get_items_to_fetch(item_codes, force_update)
    if not items_to_fetch:
        return FetchItemsResult(unsuccessful=[], successful=[])

    parsed_items = ikea_api_wrapped.get_items(items_to_fetch)

    _create_item_categories(parsed_items)
    _fetch_child_items(parsed_items, force_update)

    fetched_item_codes: list[str] = []
    for parsed_item in parsed_items:
        _make_items_from_child_items_if_not_exist(parsed_item)
        _create_item(parsed_item)
        fetched_item_codes.append(parsed_item["item_code"])

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
            and isinstance(e.args[0], list)
            and len(e.args[0]) > 0  # type: ignore
            and isinstance(e.args[0][0], str)
        ):
            raise

        # If error has this format: ItemFetchError(["item_code", ...])
        if unsuccessful := ikea_api_wrapped.parse_item_codes(e.args[0]):  # type: ignore
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
