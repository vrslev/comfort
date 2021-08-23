from __future__ import annotations

import asyncio
import re
from collections import Counter
from typing import TypedDict

import aiohttp

import frappe
from comfort import ValidationError, count_quantity
from frappe import _
from frappe.model.document import Document

from ..child_item.child_item import ChildItem
from ..item_category_table.item_category_table import ItemCategoryTable


class ItemMethods:
    image: str
    item_code: str
    item_name: str
    item_categories: list[ItemCategoryTable]
    url: str | None
    rate: int
    weight: float
    child_items: list[ChildItem]

    def validate_child_items(self):
        if self.child_items and frappe.db.exists(
            "Child Item", {"parent": ["in", [d.item_code for d in self.child_items]]}
        ):
            raise ValidationError(_("Can't add child item that contains child items"))

    def validate_url(self):
        if self.url:
            if len(re.findall(r"ikea.com/\w+/\w+/p/-s?\d+", self.url)) == 0:
                raise ValidationError(_("Invalid URL"))

    def set_name(self):
        if not self.item_name:
            self.item_name = self.item_code

    def calculate_weight(self):
        if not (self.child_items and len(self.child_items) > 0):
            return

        items: list[Item] = frappe.get_all(
            "Item",
            ["item_code", "weight"],
            {"item_code": ["in", [d.item_code for d in self.child_items]]},
        )
        weight_map: Counter[str] = count_quantity(items, "item_code", "weight")
        self.weight = 0
        for d in self.child_items:
            self.weight += weight_map[d.item_code] * d.qty

    def calculate_weight_in_parent_docs(self):
        parent_items: list[ChildItem] = frappe.get_all(
            "Child Item", "parent", {"item_code": self.item_code}
        )
        parent_item_names = list({d.parent for d in parent_items})
        for d in parent_item_names:
            doc: Item = frappe.get_doc("Item", d)
            doc.calculate_weight()
            doc.db_update()


class Item(Document, ItemMethods):
    def validate(self):
        self.validate_child_items()
        self.validate_url()
        self.set_name()
        self.calculate_weight()

    def on_change(self):
        self.clear_cache()

    def on_update(self):
        self.calculate_weight_in_parent_docs()


def _save_image(item_code: str, image_url: str, content: bytes):
    fpath = f"files/items/{item_code}"
    fname = f"{image_url.rsplit('/', 1)[1]}"
    site_path = frappe.get_site_path("public", fpath)

    frappe.create_folder(site_path)
    with open(f"{site_path}/{fname}", "wb+") as f:
        f.write(content)

    frappe.db.set_value("Item", item_code, "image", f"/{fpath}/{fname}")


class ImageItem(TypedDict):
    item_code: str
    image_url: str


def download_images(items: list[ImageItem]):
    async def fetch(session: aiohttp.ClientSession, item: ImageItem):
        async with session.get(item["image_url"]) as r:
            content = await r.content.read()
        _save_image(content=content, **item)

    async def main(items: list[ImageItem]):
        async with aiohttp.ClientSession() as session:
            tasks = [fetch(session, item) for item in items]
            return await asyncio.gather(*tasks)

    item_codes = [item["item_code"] for item in items]
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
