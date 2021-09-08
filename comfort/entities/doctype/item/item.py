from __future__ import annotations

import re
from collections import Counter

import frappe
from comfort import ValidationError, count_qty
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
            if len(re.findall(r"ikea.com/ru/ru/p/[^/]+s?\d+", self.url)) == 0:
                raise ValidationError(_("Invalid URL"))

    def set_name(self):
        if not self.item_name:
            self.item_name = self.item_code

    def calculate_weight(self):
        if not (self.child_items and len(self.child_items) > 0):
            return

        items: list[Item] = frappe.get_all(
            "Item",
            fields=("item_code", "weight"),
            filters={"item_code": ("in", (d.item_code for d in self.child_items))},
        )
        weight_map: Counter[str] = count_qty(items, "item_code", "weight")
        self.weight = 0
        for d in self.child_items:
            self.weight += weight_map[d.item_code] * d.qty

    def calculate_weight_in_parent_docs(self):
        parent_items: list[ChildItem] = frappe.get_all(
            "Child Item", "parent", {"item_code": self.item_code}
        )
        parent_item_names = list({d.parent for d in parent_items})
        for d in parent_item_names:
            if frappe.db.exists("Item", d):
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
