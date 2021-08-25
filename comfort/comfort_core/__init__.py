import frappe
from comfort.comfort_core.ikea import FetchItemsResult, fetch_items
from comfort.entities.doctype.item.item import Item


@frappe.whitelist()
def get_items(item_codes: str) -> list[Item]:  # pragma: no cover
    response: FetchItemsResult = fetch_items(item_codes)
    if response["unsuccessful"]:
        frappe.msgprint(
            "Эти товары не удалось загрузить: " + ", ".join(response["unsuccessful"])
        )
    return frappe.get_all(
        "Item",
        fields=("item_code", "item_name", "rate", "weight"),
        filters={"item_code": ("in", response["successful"])},
    )
