from __future__ import annotations

import frappe
from comfort import get_doc, get_value, new_doc
from comfort.entities.doctype.customer.customer import Customer, parse_vk_url
from comfort.integrations.ikea import fetch_items
from comfort.transactions.doctype.sales_order.sales_order import SalesOrder
from frappe.model.rename_doc import rename_doc
from frappe.utils import get_url_to_form


def _create_customer(name: str, vk_url: str):
    if doc_name := get_value("Customer", {"vk_id": parse_vk_url(vk_url).vk_id}):
        if doc_name != name:
            doc_name: str = rename_doc("Customer", doc_name, name)  # type: ignore
        doc = get_doc(Customer, doc_name)
    else:
        doc = new_doc(Customer)
        doc.name = name
        doc.vk_url = vk_url
        doc.insert()
    return doc


def _create_sales_order(customer_name: str, item_codes: list[str]):
    fetch_result = fetch_items(item_codes, force_update=True)
    if not fetch_result["successful"]:
        return

    doc = new_doc(SalesOrder)
    doc.customer = customer_name
    doc.extend(
        "items",
        [
            {"item_code": item_code, "qty": 1}
            for item_code in fetch_result["successful"]
        ],
    )
    doc.save()
    return doc


def _get_url_to_reference_doc(
    customer: Customer, sales_order: SalesOrder | None
) -> str:
    ref_doc = sales_order if sales_order is not None else customer
    return get_url_to_form(ref_doc.doctype, ref_doc.name)  # type: ignore


@frappe.whitelist()
def main(customer_name: str, vk_url: str, item_codes: list[str]):  # pragma: no cover
    customer = _create_customer(customer_name, vk_url)
    sales_order = _create_sales_order(customer_name, item_codes)
    return _get_url_to_reference_doc(customer, sales_order)
