from __future__ import annotations

import asyncio
from typing import Any

import aiohttp
import ikea_api_wrapped
from ikea_api.errors import ItemFetchError
from ikea_api_wrapped import get_item_codes
from ikea_api_wrapped.wrappers import AnyParsedItem, NoDeliveryOptionsAvailableError

import frappe
from comfort import ValidationError, maybe_json
from comfort.comfort_core.doctype.ikea_settings.ikea_settings import (
    get_authorized_api,
    get_guest_api,
)
from comfort.entities.doctype.item.item import Item
from comfort.entities.doctype.item_category.item_category import ItemCategory
from frappe import _


def get_delivery_services(items: dict[str, int]):
    api = get_guest_api()
    zip_code: str = frappe.get_cached_value(
        "Ikea Settings", "Ikea Settings", "zip_code"
    )
    try:
        return ikea_api_wrapped.get_delivery_services(api, items, zip_code)
    except NoDeliveryOptionsAvailableError:
        frappe.msgprint("Нет доступных способов доставки", alert=True, indicator="red")


def add_items_to_cart(items: dict[str, int], authorize: bool):
    api = get_authorized_api() if authorize else get_guest_api()
    return ikea_api_wrapped.add_items_to_cart(api, items)


def get_purchase_history():
    return ikea_api_wrapped.get_purchase_history(get_authorized_api())


def get_purchase_info(purchase_id: int, use_lite_id: bool):
    email: str | None = None
    if use_lite_id:
        email = frappe.get_cached_value("Ikea Settings", "Ikea Settings", "username")
    return ikea_api_wrapped.get_purchase_info(get_authorized_api(), purchase_id, email)


@frappe.whitelist()
def fetch_new_items(
    item_codes: list[Any] | int | str,
    force_update: bool = False,
    download_images: bool = True,
    values_from_db: list[str] | None = None,
) -> dict[str, list[Any]]:
    force_update = maybe_json(force_update)
    download_images = maybe_json(download_images)
    values_from_db = maybe_json(values_from_db)

    item_codes = get_item_codes(item_codes)

    items_to_fetch: list[str] = []
    exist: list[str] = [
        d.name
        for d in frappe.get_all("Item", "name", {"item_code": ["in", item_codes]})
    ]
    for d in item_codes:
        if d not in exist or force_update:
            items_to_fetch.append(d)

    res: dict[str, Any] = {
        "fetched": [],
        "already_exist": exist,
        "unsuccessful": [],
        "successful": item_codes,
    }

    parsed_items: list[Any] = []
    if len(items_to_fetch) > 0:
        try:
            response: dict[str, Any] = ikea_api_wrapped.get_items(items_to_fetch)
        except ItemFetchError as e:
            if "Wrong Item Code" in e.args[0]:
                raise ValidationError(_("Wrong Item Code"))
            raise

        parsed_items: list[AnyParsedItem] = response["items"]
        res.update(
            {
                "unsuccessful": response["unsuccessful"],
                "fetched": response["fetched"],
                "successful": [
                    d for d in item_codes if d not in response["unsuccessful"]
                ],
            }
        )

        for d in parsed_items:
            add_item(d, force_update=force_update)

    if values_from_db and len(values_from_db) > 0:
        if "item_code" in values_from_db:
            values_from_db.remove("item_code")
        values_from_db.insert(0, "item_code")

        res["values"] = frappe.get_all(
            "Item", values_from_db, {"item_code": ["in", res["successful"]]}
        )

    if download_images and parsed_items:
        frappe.enqueue(
            "comfort.comfort_core.ikea.item.download_items_images",
            items=[
                {"item_code": d.item_code, "image_url": d.image_url}
                for d in parsed_items
                if d.item_code in res["fetched"] and d.image_url
            ],
            queue="short",
        )

    return res


def _fetch_items(
    item_codes: list[str | int] | int | str, force_update: bool
) -> dict[str, list[str]]:
    item_codes = get_item_codes(item_codes)

    exist: list[str] = [
        d.name
        for d in frappe.get_all("Item", "item_code", {"item_code": ("in", item_codes)})
    ]
    items_to_fetch: list[str] = [item for item in item_codes if item not in exist]
    if not items_to_fetch:
        return {"unsuccessful": []}

    response: dict[str, Any] = ikea_api_wrapped.get_items(items_to_fetch)

    parsed_items: list[AnyParsedItem] = response["items"]
    for parsed_item in parsed_items:
        add_item(parsed_item, force_update=force_update)

    return {"unsuccessful": response["unsuccessful"]}


def _save_image(item_code: str, image_url: str, content: bytes):
    fpath = f"files/items/{item_code}"
    fname = f"{image_url.rsplit('/', 1)[1]}"
    site_path = frappe.get_site_path("public", fpath)

    frappe.create_folder(site_path)
    with open(f"{site_path}/{fname}", "wb+") as f:
        f.write(content)

    frappe.db.set_value("Item", item_code, "image", f"/{fpath}/{fname}")


def download_items_images(items: list[dict[str, Any]]):
    async def fetch(session: aiohttp.ClientSession, item: dict[str, Any]):
        async with session.get(item["image_url"]) as r:
            content = await r.content.read()
        _save_image(content=content, **item)

    async def main(items: list[dict[str, Any]]):
        async with aiohttp.ClientSession() as session:
            tasks = [fetch(session, item) for item in items]
            return await asyncio.gather(*tasks)

    item_codes: list[str] = [item["item_code"] for item in items]
    items_have_image: list[str] = [
        item.item_code
        for item in frappe.get_all(
            "Item",
            fields=["item_code", "image"],
            filters={"item_code": ("in", item_codes)},
        )
        if item.image
    ]

    items_to_fetch = [item for item in items if item not in items_have_image]
    if not items_to_fetch:
        return

    asyncio.run(main(items_to_fetch))
    frappe.db.commit()


def _make_item_category(name: str, url: str) -> ItemCategory | None:
    if not frappe.db.exists("Item Category", name):
        return frappe.get_doc(
            {
                "doctype": "Item Category",
                "item_category_name": name,
                "url": url,
            }  # TODO: Maybe unify and use NAME field instead of ITEM_CATEGORY_NAME?
        ).insert()


def _make_item(
    item_code: str,
    name: str,
    weight: float,
    category_name: str | None = None,
    rate: int = 0,
    url: str | None = None,
    child_items: list[Any] | None = None,
) -> Item:
    if frappe.db.exists("Item", item_code):
        doc: Item = frappe.get_doc("Item", item_code)
        doc.item_name = name
        doc.item_categories = []
        doc.append("item_categories", {"item_category": category_name})
        doc.url = url
        doc.rate = rate
        doc.weight = weight
        if child_items:
            current_child_items: tuple[dict[str, str | int]] = (
                {"item_code": d.item_code, "qty": d.qty} for d in doc.child_items
            )
            new_child_items: list[dict[str, str | int]] = [
                {"item_code": d["item_code"], "qty": d["qty"]} for d in child_items
            ]
            if (
                len(
                    child
                    for child in current_child_items
                    if child not in new_child_items
                )
                > 0
            ):
                doc.child_items = []
                doc.extend("child_items", child_items)
        doc.save()

    else:
        doc: Item = frappe.get_doc(
            {
                "doctype": "Item",
                "item_code": item_code,
                "item_name": name,
                "url": url,
                "rate": rate,
                "weight": weight,
                "child_items": child_items,
            }
        )
        if category_name:
            doc.append("item_categories", {"item_category": category_name})
        doc.insert()

    return doc


def add_item(item: AnyParsedItem, force_update: bool):
    _make_item_category(item["category_name"], item["category_url"])
    if item["is_combination"]:
        fetch_new_items(
            [child["item_code"] for child in item["child_items"]],
            force_update=force_update,
        )
    _make_item(
        item_code=item["item_code"],
        name=item["name"],
        weight=item["weight"],
        category_name=item["category_name"],
        rate=item["price"],
        url=item["url"],
        child_items=item["child_items"],
    )
