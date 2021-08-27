from __future__ import annotations

import re
from typing import Any, Literal
from urllib.parse import urlencode

import telegram
from ikea_api_wrapped import format_item_code

import frappe
from comfort import ValidationError, maybe_json
from comfort.comfort_core.doctype.telegram_settings.telegram_settings import (
    send_message,
)
from comfort.stock.doctype.delivery_stop.delivery_stop import DeliveryStop
from comfort.transactions.doctype.sales_order.sales_order import SalesOrder
from comfort.transactions.doctype.sales_order_service.sales_order_service import (
    SalesOrderService,
)
from frappe import _
from frappe.model.document import Document
from frappe.utils import get_url_to_form


class DeliveryTrip(Document):
    stops: list[DeliveryStop]
    status: Literal["Draft", "In Progress", "Completed", "Cancelled"]

    def before_insert(self):  # pragma: no cover
        self.set_status()

    def before_submit(self):  # pragma: no cover
        self.set_status()
        self._validate_stops_have_address_and_city()
        self._validate_orders_have_services()

    def before_cancel(self):  # pragma: no cover
        self.set_status()

    def set_status(self):
        self.status = {0: "Draft", 1: "In Progress", 2: "Cancelled"}[self.docstatus]

    def _validate_stops_have_address_and_city(self):
        for stop in self.stops:
            if not stop.address:
                raise ValidationError(_("Every stop should have address"))
            if not stop.city:
                raise ValidationError(_("Every stop should have city"))

    def _validate_orders_have_services(self):
        for stop in self.stops:
            res = get_delivery_and_installation_for_order(stop.sales_order)
            if res["delivery_type"] is None:
                raise ValidationError(  # pragma: no cover ???
                    _("Sales Order {} has no delivery service").format(stop.sales_order)
                )
            if stop.installation and not res["installation"]:
                raise ValidationError(
                    _("Sales Order {} has no installation service").format(
                        stop.sales_order
                    )
                )

    def _get_template_context(self):
        context: dict[str, str | list[dict[str, Any]]] = {
            "form_url": get_url_to_form("Delivery Trip", self.name),
            "doctype": _("Delivery Trip"),
            "docname": self.name,
            "stops": [],
        }

        for stop in self.stops:
            context["stops"].append(
                {
                    "customer": stop.customer,
                    "delivery_type": stop.delivery_type,
                    "phone": stop.phone,
                    "route_url": _make_route_url(stop.city, stop.address),
                    "address": stop.address,
                    "pending_amount": stop.pending_amount,
                    "details": stop.details,
                    "items_": _get_items_for_order(stop.sales_order),
                }
            )
        return context

    @frappe.whitelist()
    def render_telegram_message(self) -> str:
        return frappe.render_template(
            "stock/doctype/delivery_trip/telegram_template.j2",
            self._get_template_context(),
            is_path=True,
        )


def _make_route_url(city: str, address: str):
    url = "https://yandex.ru/maps/10849/severodvinsk/?"
    params = {"text": city + " " + address}
    return url + urlencode(params)


def _get_items_for_order(sales_order_name: str):  # pragma: no cover
    doc: SalesOrder = frappe.get_doc("Sales Order", sales_order_name)
    return [
        {
            "item_code": format_item_code(i.item_code),
            "qty": i.qty,
            "item_name": i.item_name,
        }
        for i in doc._get_items_with_splitted_combinations()
    ]


@frappe.whitelist()
def get_delivery_and_installation_for_order(sales_order_name: str):
    services: list[SalesOrderService] = frappe.get_all(
        "Sales Order Service", filters={"parent": sales_order_name}, fields="type"
    )
    res = {"delivery_type": None, "installation": False}
    for service in services:
        if service.type == "Delivery to Apartment":
            res["delivery_type"] = "To Apartment"
        if service.type == "Delivery to Entrance":
            res["delivery_type"] = "To Entrance"
        elif service.type == "Installation":
            res["installation"] = True
    return res


def _prepare_message_for_telegram(message: str):
    message = message.replace("\n", "").replace("<br>", "\n")
    message = re.sub(r" +", " ", message)
    message = message.replace("&nbsp;&nbsp;&nbsp;", "   ")
    return message


@frappe.whitelist()
def send_telegram_message(text: str):  # pragma: no cover
    send_message(
        text=_prepare_message_for_telegram(maybe_json(text)),
        parse_mode=telegram.ParseMode.HTML,
        disable_web_page_preview=True,
    )
