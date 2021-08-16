from __future__ import annotations

import asyncio
import json
from typing import Any, Coroutine

import aiohttp
from ikea_api.errors import ItemFetchError
from ikea_api_extender import get_items_immortally

import frappe
from comfort import ValidationError
from comfort.comfort_core.ikea.utils import (
    extract_item_codes,
    get_item_codes_from_ingka_pagelinks,
)
from comfort.entities.doctype.item.item import Item
from comfort.entities.doctype.item_category.item_category import ItemCategory
from frappe import _
from frappe.utils import parse_json


@frappe.whitelist()
def fetch_new_items(
    item_codes: str | list[Any],
    force_update: str | bool = False,
    download_images: str | bool = True,
    values_from_db: str | list[str] = [],
) -> dict[str, list[Any]]:

    if not isinstance(item_codes, list):
        try:
            item_codes = json.loads(item_codes)
        except json.decoder.JSONDecodeError:
            item_codes = str(item_codes)

    force_update, download_images, values_from_db = (
        parse_json(force_update),
        parse_json(download_images),
        parse_json(values_from_db),
    )

    if isinstance(item_codes, int):
        item_codes = str(item_codes)
    if isinstance(item_codes, str):
        if "ingka.page.link/[0-9A-z]+" in item_codes:
            item_codes = get_item_codes_from_ingka_pagelinks(item_codes)
        else:
            item_codes = extract_item_codes(item_codes)

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

    parsed_items = None
    if len(items_to_fetch) > 0:
        try:
            response: list[Any] = get_items_immortally(items_to_fetch)
        except ItemFetchError as e:
            if "Wrong Item Code" in e.args[0]:
                raise ValidationError(_("Wrong Item Code"))
            else:
                raise

        parsed_items: list[Any] = response["items"]
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
                if d.item_code in res["fetched"]
            ],
            queue="short",
        )

    return res


def download_items_images(items: dict[str, Any]):
    async def fetch(session: aiohttp.ClientSession, item: dict[str, Any]):
        if not item["image_url"]:
            return

        async with session.get(item["image_url"]) as r:
            content: Any = await r.content.read()

        fpath = f"files/items/{item['item_code']}"
        fname = f"{item['image_url'].rsplit('/', 1)[1]}"
        site_path = frappe.get_site_path("public", fpath)

        frappe.create_folder(site_path)
        with open(f"{site_path}/{fname}", "wb+") as f:
            f.write(content)

        dt = "Item"
        frappe.db.set_value(
            dt,
            item["item_code"],  # type: ignore
            "image",
            f"/{fpath}/{fname}",
            update_modified=False,
        )

    async def main(items: dict[str, Any]):
        async with aiohttp.ClientSession() as session:
            tasks: list[Coroutine[Any, Any, None]] = []
            for d in items:
                task = fetch(session, d)
                tasks.append(task)
            results = await asyncio.gather(*tasks)
            return results

    have_image: list[str] = [
        d.item_code
        for d in frappe.get_all(
            "Item",
            ["item_code", "image"],
            {"item_code": ["in", [d["item_code"] for d in items]]},
        )
        if d.image
    ]
    items = [d for d in items if d not in have_image]

    if len(items) > 0:
        asyncio.run(main(items))
        frappe.db.commit()


def add_item(item: Any, force_update: bool):
    _make_item_category(item.group_name, item.group_url)
    if item.is_combination:
        response = fetch_new_items(
            [d["item_code"] for d in item.bundle_items], force_update=force_update
        )
        for d in response["unsuccessful"]:
            _make_item(d["item_code"], d["item_name"], d["weight"])
    _make_item(
        item.item_code,
        item.name,
        item.weight,
        item.group_name,
        item.price,
        item.url,
        item.bundle_items,
    )


def _make_item_category(name: str, url: str) -> ItemCategory | None:
    if not frappe.db.exists("Item Category", name):
        return frappe.get_doc(
            {"doctype": "Item Category", "item_category_name": name, "url": url}
        ).insert()


def _make_item(
    item_code: str,
    item_name: str,
    weight: float,
    item_category: str | None = None,
    rate: int = 0,
    url: str | None = None,
    child_items: list[Any] = [],
) -> Item:
    if frappe.db.exists("Item", item_code):
        doc: Item = frappe.get_doc("Item", item_code)
        doc.item_name = item_name
        categories: list[str] = [d.item_category for d in doc.item_categories]
        if item_category not in categories:
            doc.append("item_categories", {"item_category": item_category})
        doc.url = url
        doc.rate = rate
        doc.weight = weight
        if child_items and len(child_items) > 0:
            cur_child_items: list[dict[str, str | int]] = [
                {"item_code": d.item_code, "qty": d.qty} for d in doc.child_items
            ]
            new_child_items: list[dict[str, str | int]] = [
                {"item_code": d["item_code"], "qty": d["qty"]} for d in child_items
            ]
            if len([d for d in cur_child_items if d not in new_child_items]) > 0:
                doc.child_items = []
                doc.extend("child_items", child_items)
        doc.save()
    else:
        doc: Item = frappe.get_doc(
            {
                "doctype": "Item",
                "item_code": item_code,
                "item_name": item_name,
                "url": url,
                "rate": rate,
                "weight": weight,
                "child_items": child_items,
            }
        )
        if item_category:
            doc.append("item_categories", {"item_category": item_category})
        doc.insert()
    return doc
