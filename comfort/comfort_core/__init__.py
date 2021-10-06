import frappe
from comfort import get_all
from comfort.comfort_core.ikea import fetch_items
from comfort.entities.doctype.item.item import Item


@frappe.whitelist()
def get_items(item_codes: str):  # pragma: no cover
    response = fetch_items(item_codes, force_update=True)
    if response["unsuccessful"]:
        frappe.msgprint(
            "Эти товары не удалось загрузить: " + ", ".join(response["unsuccessful"])
        )
    return get_all(
        Item,
        fields=("item_code", "item_name", "rate", "weight"),
        filters={"item_code": ("in", response["successful"])},
    )
