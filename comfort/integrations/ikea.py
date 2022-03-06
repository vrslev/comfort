from __future__ import annotations

from calendar import timegm
from datetime import date, datetime, timezone
from functools import lru_cache
from typing import TypedDict, cast

import ikea_api
import sentry_sdk
from ikea_api import format_item_code as format_item_code  # For jenv hook
from ikea_api.utils import (
    unshorten_urls_from_ingka_pagelinks as orig_unshorten_urls_from_ingka_pagelinks,
)
from ikea_api.wrappers import types
from ikea_api.wrappers.parsers.iows_items import get_url as get_short_url
from jwt import PyJWT
from jwt.exceptions import ExpiredSignatureError

import frappe
from comfort import (
    ValidationError,
    _,
    count_qty,
    counters_are_same,
    doc_exists,
    get_all,
    get_cached_doc,
    get_cached_value,
    get_doc,
    new_doc,
    syncify,
)
from comfort.comfort_core.doctype.ikea_settings.ikea_settings import IkeaSettings
from comfort.entities.doctype.item.item import Item
from comfort.entities.doctype.item_category.item_category import ItemCategory
from frappe.utils import add_to_date, get_datetime, now_datetime

__all__ = [
    "get_constants",
    "get_guest_token",
    "get_auth_token",
    "get_delivery_services",
    "add_items_to_cart",
]


@lru_cache
def get_constants():
    return ikea_api.Constants(country="ru", language="ru")


def _should_renew_guest_token(doc: IkeaSettings):
    return any(
        (
            not doc.guest_token,
            not doc.guest_token_expiration,
            get_datetime(doc.guest_token_expiration) <= now_datetime(),  # type: ignore
        )
    )


def _get_guest_token() -> str:
    return ikea_api.run(ikea_api.Auth(get_constants()).get_guest_token())


def _set_renew_guest_token(doc: IkeaSettings):
    doc.guest_token = _get_guest_token()
    doc.guest_token_expiration = add_to_date(None, days=30)
    doc.save()


def get_guest_token():
    doc = get_cached_doc(IkeaSettings)
    if _should_renew_guest_token(doc):
        _set_renew_guest_token(doc)
    assert doc.guest_token
    return doc.guest_token


def _auth_token_expired(exp: int):
    now = timegm(datetime.now(tz=timezone.utc).utctimetuple())
    try:
        PyJWT()._validate_exp({"exp": exp}, now, 0)
    except ExpiredSignatureError:
        return True


def _should_renew_auth_token(doc: IkeaSettings):
    return any(
        (
            not doc.authorized_token,
            not doc.authorized_token_expiration,
            _auth_token_expired(doc.authorized_token_expiration),  # type: ignore
        )
    )


def get_auth_token() -> str:
    doc = get_cached_doc(IkeaSettings)
    if _should_renew_auth_token(doc):
        raise ValidationError(_("Update authorization info"))
    assert doc.authorized_token
    return doc.authorized_token


def _get_zip_code():
    zip_code: str | None = get_cached_value(
        "Ikea Settings", "Ikea Settings", "zip_code"
    )
    if not zip_code:
        raise ValidationError(_("Enter Zip Code in Ikea Settings"))
    return zip_code


def _get_delivery_services(items: dict[str, int]) -> types.GetDeliveryServicesResponse:
    coro = ikea_api.get_delivery_services(
        constants=get_constants(),
        token=get_guest_token(),
        items=items,
        zip_code=_get_zip_code(),
    )
    return syncify.run(coro)


def _validate_delivery_services_items(items: dict[str, int]):
    if sum(items.values()) == 0:
        raise ValidationError(_("No items selected to check delivery services"))


def _check_delivery_services_response(response: types.GetDeliveryServicesResponse):
    if response.delivery_options:
        return True

    frappe.msgprint(_("No available delivery options"), alert=True, indicator="red")


def get_delivery_services(items: dict[str, int]):
    _validate_delivery_services_items(items)
    response = _get_delivery_services(items)
    if _check_delivery_services_response(response):
        return response


def _validate_cart_items(items: dict[str, int]):
    if sum(items.values()) == 0:
        raise ValidationError(_("No items selected to add to cart"))


def _add_items_to_cart(items: dict[str, int], authorize: bool):
    token = get_auth_token() if authorize else get_guest_token()
    cart = ikea_api.Cart(constants=get_constants(), token=token)
    return ikea_api.add_items_to_cart(cart=cart, items=items)


def add_items_to_cart(items: dict[str, int], authorize: bool):
    _validate_cart_items(items)
    return _add_items_to_cart(items, authorize)


def _get_purchase_history():
    purchases = ikea_api.Purchases(constants=get_constants(), token=get_auth_token())
    return ikea_api.get_purchase_history(purchases=purchases)


@frappe.whitelist()
def get_purchase_history():
    return [p.dict() for p in _get_purchase_history()]


class PurchaseInfoDict(TypedDict):
    delivery_cost: float
    total_cost: float
    purchase_date: date | None
    delivery_date: date | None


def _get_purchase_info(purchase_id: str) -> PurchaseInfoDict:
    purchases = ikea_api.Purchases(constants=get_constants(), token=get_auth_token())
    return cast(
        PurchaseInfoDict,
        ikea_api.get_purchase_info(
            purchases=purchases, order_number=purchase_id
        ).dict(),
    )


def _handle_purchase_info_error(exc: ikea_api.GraphQLError):
    skip_messages = (
        "Purchase not found",
        "Order not found",
        "Invalid order id",
        "Exception while fetching data (/order/id) : null",
    )
    for error in exc.errors:
        if error.get("message") in skip_messages:
            return
    sentry_sdk.capture_exception(exc)


def _retry_get_purchase_info(purchase_id: str):
    for _ in range(3):
        try:
            return _get_purchase_info(purchase_id=purchase_id)
        except ikea_api.APIError as exc:
            if exc.response.status_code != 504:
                raise


@frappe.whitelist()
def get_purchase_info(purchase_id: str):
    try:
        return _retry_get_purchase_info(purchase_id)
    except ikea_api.GraphQLError as exc:
        _handle_purchase_info_error(exc)


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


def _shorten_item_url_if_required(item: types.ParsedItem):
    if len(item.url) < 140:
        return item.url

    return get_short_url(
        constants=get_constants(),
        item_code=item.item_code,
        is_combination=item.is_combination,
    )


def _create_item(parsed_item: types.ParsedItem):
    if doc_exists("Item", parsed_item.item_code):
        doc = get_doc(Item, parsed_item.item_code)
        doc.item_name = parsed_item.name
        doc.url = _shorten_item_url_if_required(parsed_item)
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
        doc.url = _shorten_item_url_if_required(parsed_item)
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


def _unshorten_urls_from_ingka_pagelinks(item_codes: str | list[str]) -> list[str]:
    coro = orig_unshorten_urls_from_ingka_pagelinks(str(item_codes))
    return syncify.run(coro)


def parse_item_codes(item_codes: str | list[str]) -> list[str]:
    if isinstance(item_codes, str):
        res = [item_codes]
    else:
        res = item_codes
    unshortened = _unshorten_urls_from_ingka_pagelinks(res[0]) if res else []
    res.extend(unshortened)
    return ikea_api.parse_item_codes(res)


def _get_items_to_fetch(item_codes: str | list[str], force_update: bool):
    parsed_item_codes = parse_item_codes(item_codes)

    if force_update:
        return parsed_item_codes
    else:
        exist: list[str] = get_all(
            Item,
            pluck="item_code",
            field="item_code",
            filter={"item_code": ("in", parsed_item_codes)},
        )
        return [i for i in parsed_item_codes if i not in exist]


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


def _get_items(item_codes: list[str]) -> list[types.ParsedItem]:
    coro = ikea_api.get_items(constants=get_constants(), item_codes=item_codes)
    return syncify.run(coro)


def fetch_items(item_codes: str | list[str], force_update: bool):
    items_to_fetch = _get_items_to_fetch(item_codes, force_update)
    if not items_to_fetch:
        return FetchItemsResult(unsuccessful=[], successful=[])

    parsed_items = _get_items(items_to_fetch)

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
    except ikea_api.ItemFetchError as e:
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
        field=("item_code", "item_name", "rate", "weight"),
        filter={"item_code": ("in", response["successful"])},
    )
