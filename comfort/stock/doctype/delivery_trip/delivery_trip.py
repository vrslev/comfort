from __future__ import annotations

from typing import Any, Literal, TypedDict
from urllib.parse import urlencode

import frappe
from comfort import TypedDocument, ValidationError, _, get_all, get_doc, group_by_attr
from comfort.entities.doctype.customer.customer import Customer
from comfort.stock.doctype.receipt.receipt import Receipt
from comfort.transactions.doctype.sales_order.sales_order import SalesOrder
from comfort.transactions.doctype.sales_order_service.sales_order_service import (
    SalesOrderService,
)
from frappe.utils import get_url_to_form

from ..delivery_stop.delivery_stop import DeliveryStop


class DeliveryTrip(TypedDocument):
    stops: list[DeliveryStop]
    weight: float
    status: Literal["Draft", "In Progress", "Completed", "Cancelled"]

    def before_insert(self):  # pragma: no cover
        self.set_status()

    def before_submit(self):  # pragma: no cover
        self.set_status()
        self._validate_stops_have_address_and_city()
        self._validate_orders_have_delivery_services()

    def before_cancel(self):  # pragma: no cover
        self.set_status()

    def validate(self):  # pragma: no cover
        self._validate_delivery_statuses_in_orders()
        self.update_sales_orders_from_db()
        self._get_weight()

    def _validate_delivery_statuses_in_orders(self):
        orders = get_all(
            SalesOrder,
            fields=("name", "delivery_status"),
            filters={"name": ("in", (s.sales_order for s in self.stops))},
        )
        for order in orders:
            if order.delivery_status == "To Deliver":
                continue
            raise ValidationError(
                _(
                    "Can only deliver Sales Orders that have delivery status To Deliver: {}"
                ).format(order.name)
            )

    def update_sales_orders_from_db(self):
        order_names = [s.sales_order for s in self.stops]
        grouped_orders_with_customer = group_by_attr(
            data=get_all(
                SalesOrder,
                fields=("name", "customer", "pending_amount"),
                filters={"name": ("in", order_names)},
            ),
            attr="name",
        )

        # + 1 loop to be able to get customer additional info later
        for stop in self.stops:
            sales_order = grouped_orders_with_customer[stop.sales_order][0]
            stop.customer = sales_order.customer
            stop.pending_amount = sales_order.pending_amount

        grouped_services = group_by_attr(
            data=get_all(
                SalesOrderService,
                fields=("parent", "type"),
                filters={"parent": ("in", order_names)},
            ),
            attr="parent",
        )
        grouped_customers = group_by_attr(
            data=get_all(
                Customer,
                fields=("name", "address", "city", "phone"),
                filters={"name": ("in", (s.customer for s in self.stops))},
            ),
            attr="name",
        )

        for stop in self.stops:
            if services := grouped_services.get(stop.sales_order):
                delivery_and_installation = (
                    _get_delivery_and_installation_from_services(services)
                )
                stop.delivery_type = delivery_and_installation["delivery_type"]
                stop.installation = delivery_and_installation["installation"]

            customer = grouped_customers[stop.customer][0]
            stop.address = customer.address
            stop.city = customer.city
            stop.phone = customer.phone

    def _get_weight(self):
        v: list[Any] = get_all(
            SalesOrder,
            fields="SUM(total_weight) as weight",
            filters={"name": ("in", (s.sales_order for s in self.stops))},
        )
        self.weight = v[0].weight

    def set_status(self):
        docstatus_to_status_map: dict[
            int, Literal["Draft", "In Progress", "Cancelled"]
        ] = {0: "Draft", 1: "In Progress", 2: "Cancelled"}
        self.status = docstatus_to_status_map[self.docstatus]

    def _validate_stops_have_address_and_city(self):
        for stop in self.stops:
            if not stop.address:
                raise ValidationError(_("Every stop should have address"))
            if not stop.city:
                raise ValidationError(_("Every stop should have city"))

    def _validate_orders_have_delivery_services(self):
        for stop in self.stops:
            if not stop.delivery_type:
                raise ValidationError(
                    _("Sales Order {} has no delivery service").format(stop.sales_order)
                )

    def _get_template_context(self):
        context: dict[str, Any] = {
            "form_url": get_url_to_form("Delivery Trip", self.name),
            "doctype": _(self.doctype),
            "docname": self.name,
            "weight": self.weight,
            "stops": [],
        }

        stops: list[dict[str, Any]] = []
        for stop in self.stops:
            doc = get_doc(SalesOrder, stop.sales_order)
            stops.append(
                {
                    "customer": stop.customer,
                    "sales_order": stop.sales_order,
                    "delivery_type": stop.delivery_type,
                    "installation": stop.installation,
                    "phone": stop.phone,
                    "route_url": _make_route_url(stop.city, stop.address),
                    "address": stop.address,
                    "pending_amount": stop.pending_amount,
                    "details": stop.details,
                    "items_": doc.get_items_with_splitted_combinations(),
                    "weight": doc.total_weight,
                }
            )
        context["stops"] = stops
        return context

    def _add_receipts_to_sales_orders(self):
        orders_have_receipt: list[str] = [
            r.voucher_no
            for r in get_all(
                Receipt,
                fields="voucher_no",
                filters={
                    "voucher_type": "Sales Order",
                    "voucher_no": ("in", (s.sales_order for s in self.stops)),
                },
            )
        ]

        for stop in self.stops:
            if stop.sales_order not in orders_have_receipt:
                doc = get_doc(SalesOrder, stop.sales_order)
                doc.add_receipt()

    @frappe.whitelist()
    def set_completed_status(self):
        self.status = "Completed"
        self.save_without_validating()
        self._add_receipts_to_sales_orders()


def _make_route_url(city: str | None, address: str | None):
    if city and address:
        text = f"{city} {address}"
    elif city:
        text = city
    elif address:
        text = address
    else:
        return

    url = "https://yandex.ru/maps/10849/severodvinsk/?"
    return url + urlencode({"text": text})


def _get_delivery_and_installation_from_services(services: list[SalesOrderService]):
    delivery_type: str | None = None
    installation = False

    for service in services:
        if service.type == "Delivery to Apartment":
            delivery_type = "To Apartment"
        if (
            service.type == "Delivery to Entrance"
            and delivery_type is None  # Ensure "To Apartment" has advantage
        ):
            delivery_type = "To Entrance"
        elif service.type == "Installation":
            installation = True

    class GetDeliveryAndInstallationFromServicesResponse(TypedDict):
        delivery_type: Literal["To Apartment", "To Entrance"] | None
        installation: bool

    return GetDeliveryAndInstallationFromServicesResponse(
        delivery_type=delivery_type, installation=installation
    )


@frappe.whitelist()
def get_delivery_and_installation_for_order(sales_order_name: str):
    services = get_all(
        SalesOrderService, fields="type", filters={"parent": sales_order_name}
    )
    return _get_delivery_and_installation_from_services(services)
