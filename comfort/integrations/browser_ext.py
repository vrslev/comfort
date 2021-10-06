from __future__ import annotations

import re

import frappe
from comfort import doc_exists, get_doc, get_value, new_doc
from comfort.comfort_core.ikea import fetch_items
from comfort.entities.doctype.customer.customer import Customer, parse_vk_id
from comfort.transactions.doctype.sales_order.sales_order import SalesOrder
from frappe.model.rename_doc import rename_doc
from frappe.utils import get_url_to_form


def _generate_new_customer_name(name: str):
    regex = re.compile(r" (\d+)$")
    while True:
        if doc_exists("Customer", name):
            if matches := regex.findall(name):
                idx = int(matches[0]) + 1
                name = f"{regex.sub('', name)} {str(idx)}"
            else:
                name = f"{name} 2"
        else:
            break
    return name


def _create_customer(name: str, vk_url: str):
    if doc_name := get_value("Customer", {"vk_id": parse_vk_id(vk_url)}):
        if doc_name != name:
            doc_name: str = rename_doc("Customer", doc_name, name)  # type: ignore
        doc = get_doc(Customer, doc_name)
    else:
        name = _generate_new_customer_name(name)
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
