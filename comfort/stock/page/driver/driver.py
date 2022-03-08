import frappe
from comfort.stock import DeliveryTrip
from comfort.utils import doc_exists, get_doc


@frappe.whitelist()
def get_context(name: str):
    if not doc_exists("Delivery Trip", name):
        return
    return get_doc(DeliveryTrip, name)._get_template_context()
