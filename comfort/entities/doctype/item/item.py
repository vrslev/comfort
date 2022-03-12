from __future__ import annotations

import re
from collections import Counter

from comfort.utils import (
    TypedDocument,
    ValidationError,
    _,
    count_qty,
    doc_exists,
    get_all,
    get_doc,
)

from ..child_item.child_item import ChildItem
from ..item_category_table.item_category_table import ItemCategoryTable


class ItemMethods:
    image: str | None
    item_code: str
    item_name: str | None
    item_categories: list[ItemCategoryTable]
    url: str | None
    rate: int
    weight: float
    child_items: list[ChildItem]

    def validate_child_items(self):
        if self.child_items and doc_exists(
            "Child Item", {"parent": ["in", [d.item_code for d in self.child_items]]}
        ):
            raise ValidationError(_("Can't add child item that contains child items"))

    def validate_url(self):
        if self.url:
            if len(re.findall(r"ikea.com/ru/ru/p/[^/]+s?\d+", self.url)) == 0:
                raise ValidationError(_("Invalid URL"))

    def set_name(self) -> None:
        if not self.item_name:
            self.item_name = self.item_code

    def calculate_weight(self) -> None:
        if not self.child_items:
            return

        items = get_all(
            Item,
            field=("item_code", "weight"),
            filter={"item_code": ("in", (d.item_code for d in self.child_items))},
        )
        weight_map: Counter[str] = count_qty(items, "item_code", "weight")
        self.weight = 0
        for d in self.child_items:
            self.weight += weight_map[d.item_code] * d.qty

    def calculate_weight_in_parent_docs(self) -> None:
        parent_items = get_all(
            ChildItem, field="parent", filter={"item_code": self.item_code}
        )
        parent_item_names = list({d.parent for d in parent_items})
        for d in parent_item_names:
            if doc_exists("Item", d):
                doc = get_doc(Item, d)
                doc.calculate_weight()
                doc.save_without_validating()


class Item(TypedDocument, ItemMethods):
    def validate(self) -> None:
        self.validate_child_items()
        self.validate_url()
        self.set_name()
        self.calculate_weight()

    def on_change(self) -> None:
        self.clear_cache()

    def on_update(self) -> None:
        self.calculate_weight_in_parent_docs()
