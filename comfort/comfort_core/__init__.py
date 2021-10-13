import frappe
from comfort import _, get_all
from comfort.entities.doctype.item.item import Item
from comfort.integrations.ikea import fetch_items


@frappe.whitelist()
def get_items(item_codes: str):  # TODO: Cover
    response = fetch_items(item_codes, force_update=True)
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
