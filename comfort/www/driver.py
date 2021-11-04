from __future__ import annotations

from typing import Any

import frappe
from comfort import ValidationError, _, doc_exists, get_doc
from comfort.stock.doctype.delivery_trip.delivery_trip import DeliveryTrip


def get_context(context: dict[str, Any]):
    if frappe.session.user == "Guest":
        raise ValidationError(_("Log in to access this page."), frappe.PermissionError)

    delivery_trip_name: str | None = frappe.form_dict.get("name")
    if exists := bool(doc_exists("Delivery Trip", delivery_trip_name)):
        doc = get_doc(DeliveryTrip, delivery_trip_name)
        context.update(doc._get_template_context())
    context["doc_exists"] = exists
    context["no_cache"] = True
    return context
