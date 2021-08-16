# TODO: How to deal with prices that expire???

from __future__ import annotations

import re
from collections import Counter

import frappe
from comfort import ValidationError, count_quantity
from comfort.stock.doctype.bin.bin import Bin
from frappe import _
from frappe.model.document import Document

from ..child_item.child_item import ChildItem
from ..item_category_table.item_category_table import ItemCategoryTable


class ItemMethods:
    url: str | None
    child_items: list[ChildItem]
    item_code: str
    item_name: str | None
    weight: float
    rate: int
    item_categories: list[ItemCategoryTable]

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
        if self.item_name is None:
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

    def create_bin(self):
        if not self.child_items:
            bin: Bin = frappe.new_doc("Bin")
            bin.item_code = self.item_code
            bin.insert()

    def delete_bin(self):
        if not self.child_items:
            bin: Bin = frappe.get_doc("Bin", self.item_code)
            if not bin.is_empty:  # TODO: Test this
                raise ValidationError(
                    _("Can't delete item that have been used in transactions")
                )
            else:
                bin.delete()


class Item(Document, ItemMethods):  # TODO: How to cover this with tests?
    def validate(self):
        self.validate_child_items()
        self.validate_url()
        self.set_name()
        self.calculate_weight()

    def on_change(self):
        self.clear_cache()

    def on_update(self):
        self.calculate_weight_in_parent_docs()

    def after_insert(self):
        self.create_bin()

    def on_trash(self):  # pragma: no cover
        self.delete_bin()
