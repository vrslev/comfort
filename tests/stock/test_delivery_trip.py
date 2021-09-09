from __future__ import annotations

import pytest

import frappe
from comfort.entities.doctype.item.item import Item
from comfort.stock.doctype.delivery_trip.delivery_trip import (
    DeliveryTrip,
    _get_items_for_order,
    _make_route_url,
    _prepare_message_for_telegram,
    get_delivery_and_installation_for_order,
)
from comfort.transactions.doctype.sales_order.sales_order import SalesOrder
from frappe.utils import get_url_to_form


@pytest.mark.parametrize(
    ("docstatus", "expected_status"),
    ((0, "Draft"), (1, "In Progress"), (2, "Cancelled")),
)
def test_set_status(delivery_trip: DeliveryTrip, docstatus: int, expected_status: str):
    delivery_trip.db_insert()
    delivery_trip.docstatus = docstatus
    delivery_trip.set_status()
    assert delivery_trip.status == expected_status


def test_validate_stops_have_address_and_city_raises_when_no_address(
    delivery_trip: DeliveryTrip,
):
    delivery_trip.stops[0].address = None
    with pytest.raises(frappe.ValidationError, match="Every stop should have address"):
        delivery_trip._validate_stops_have_address_and_city()


def test_validate_stops_have_address_and_city_raises_when_no_city(
    delivery_trip: DeliveryTrip,
):
    delivery_trip.stops[0].city = None
    with pytest.raises(frappe.ValidationError, match="Every stop should have city"):
        delivery_trip._validate_stops_have_address_and_city()


def test_validate_orders_have_services_raises_on_no_delivery(
    delivery_trip: DeliveryTrip, sales_order: SalesOrder
):
    sales_order.services = []
    sales_order.append(
        "services",
        {
            "type": "Installation",
            "rate": 500,
        },
    )
    sales_order.save()

    with pytest.raises(
        frappe.ValidationError,
        match=f"Sales Order {sales_order.name} has no delivery service",
    ):
        delivery_trip._validate_orders_have_services()


def test_validate_orders_have_services_raises_on_no_installation(
    delivery_trip: DeliveryTrip, sales_order: SalesOrder
):
    sales_order.services = []
    sales_order.append(
        "services",
        {
            "type": "Delivery to Entrance",
            "rate": 300,
        },
    )
    sales_order.save()

    with pytest.raises(
        frappe.ValidationError,
        match=f"Sales Order {sales_order.name} has no installation service",
    ):
        delivery_trip._validate_orders_have_services()


def test_get_template_context(delivery_trip: DeliveryTrip):
    delivery_trip.set_new_name()

    context = delivery_trip._get_template_context()
    assert context["form_url"] == get_url_to_form("Delivery Trip", delivery_trip.name)
    assert context["doctype"] == "Delivery Trip"
    assert context["docname"] == delivery_trip.name

    context_stop = context["stops"][0]
    doc_stop = delivery_trip.stops[0]
    assert context_stop["customer"] == doc_stop.customer
    assert context_stop["delivery_type"] == doc_stop.delivery_type
    assert context_stop["phone"] == doc_stop.phone
    assert context_stop["route_url"] == _make_route_url(doc_stop.city, doc_stop.address)
    assert context_stop["address"] == doc_stop.address
    assert context_stop["pending_amount"] == doc_stop.pending_amount
    assert context_stop["details"] == doc_stop.details
    assert context_stop["items_"] == _get_items_for_order(doc_stop.sales_order)


def test_render_telegram_message(delivery_trip: DeliveryTrip):
    delivery_trip.set_new_name()
    delivery_trip.render_telegram_message()


@pytest.mark.parametrize("insert_receipt_before", (True, False))
def test_add_receipts_to_sales_orders(
    delivery_trip: DeliveryTrip,
    sales_order: SalesOrder,
    item_no_children: Item,
    insert_receipt_before: bool,
):
    sales_order.delivery_status = "To Deliver"
    sales_order.db_update()
    new_doc: SalesOrder = frappe.new_doc("Sales Order")
    new_doc.name = "SO-2021-0002"
    new_doc.customer = sales_order.customer
    new_doc.append("items", {"item_code": item_no_children.item_code, "qty": 1})
    new_doc.services = []
    new_doc.validate()
    new_doc.delivery_status = "To Deliver"
    new_doc.db_insert()
    new_doc.db_update_all()
    if insert_receipt_before:
        new_doc.add_receipt()

    delivery_trip.append("stops", {"sales_order": new_doc.name})
    delivery_trip._add_receipts_to_sales_orders()
    assert frappe.db.exists({"doctype": "Receipt", "voucher_no": sales_order.name})
    assert frappe.db.exists({"doctype": "Receipt", "voucher_no": new_doc.name})


def test_set_completed_status(delivery_trip: DeliveryTrip):
    delivery_trip.status = "Draft"
    for stop in delivery_trip.stops:
        frappe.db.set_value(
            "Sales Order", stop.sales_order, "delivery_status", "To Deliver"
        )
    delivery_trip.set_completed_status()
    assert delivery_trip.status == "Completed"


def test_make_route_url(delivery_trip: DeliveryTrip):
    assert (
        _make_route_url(delivery_trip.stops[0].city, delivery_trip.stops[0].address)
        == "https://yandex.ru/maps/10849/severodvinsk/?text=Moscow+Arbat%2C+1"
    )


@pytest.mark.parametrize(
    ("services", "expected_result"),
    (
        (
            [{"type": "Installation", "rate": 500}],
            {"delivery_type": None, "installation": True},
        ),
        (
            [{"type": "Delivery to Apartment", "rate": 500}],
            {"delivery_type": "To Apartment", "installation": False},
        ),
        (
            [{"type": "Delivery to Entrance", "rate": 100}],
            {"delivery_type": "To Entrance", "installation": False},
        ),
        (
            [
                {"type": "Delivery to Entrance", "rate": 100},
                {"type": "Installation", "rate": 500},
            ],
            {"delivery_type": "To Entrance", "installation": True},
        ),
    ),
)
def test_get_delivery_and_installation_for_order(
    sales_order: SalesOrder,
    services: list[dict[str, str | int]],
    expected_result: dict[str, str | bool],
):
    sales_order.services = []
    sales_order.extend("services", services)
    sales_order.db_insert()
    sales_order.db_update_all()
    res = get_delivery_and_installation_for_order(sales_order.name)
    assert res == expected_result


def test_prepare_message_for_telegram():
    assert (
        _prepare_message_for_telegram("<br><br>\n\n   &nbsp;&nbsp;&nbsp;") == "\n\n    "
    )


# TODO
# -            if stop.installation and not res["installation"]:
# +            if stop.installation or not res["installation"]:
# TODO
# -            is_path=True,
# +            is_path=False,
