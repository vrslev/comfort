from __future__ import annotations

from types import SimpleNamespace

import pytest

import frappe
from comfort import doc_exists, get_doc, new_doc
from comfort.entities.doctype.customer.customer import Customer
from comfort.entities.doctype.item.item import Item
from comfort.stock.doctype.delivery_trip.delivery_trip import (
    DeliveryTrip,
    _get_delivery_and_installation_from_services,
    _get_items_for_order,
    _make_route_url,
    _prepare_message_for_telegram,
    get_delivery_and_installation_for_order,
)
from comfort.transactions.doctype.sales_order.sales_order import SalesOrder
from frappe.utils import get_url_to_form


def test_validate_delivery_statuses_in_orders_not_raises(delivery_trip: DeliveryTrip):
    frappe.db.set_value(
        "Sales Order",
        delivery_trip.stops[0].sales_order,
        "delivery_status",
        "To Deliver",
    )
    delivery_trip._validate_delivery_statuses_in_orders()


def test_validate_delivery_statuses_in_orders_raises(delivery_trip: DeliveryTrip):
    order_name = delivery_trip.stops[0].sales_order
    frappe.db.set_value("Sales Order", order_name, "delivery_status", "Delivered")
    with pytest.raises(
        frappe.exceptions.ValidationError,
        match=f"Can only deliver Sales Orders that have delivery status To Deliver: {order_name}",
    ):
        delivery_trip._validate_delivery_statuses_in_orders()


@pytest.mark.parametrize("with_services", (True, False))
def test_delivery_trip_update_sales_orders_from_db(
    delivery_trip: DeliveryTrip, with_services: bool
):
    stop = delivery_trip.stops[0]
    stop.customer = None  # type: ignore
    stop.address = None
    stop.phone = None
    stop.pending_amount = None  # type: ignore
    stop.city = None
    stop.delivery_type = None
    stop.installation = None  # type: ignore

    sales_order = get_doc(SalesOrder, stop.sales_order)
    if not with_services:
        sales_order.services = []
    sales_order.save()
    services_resp = _get_delivery_and_installation_from_services(sales_order.services)

    customer = get_doc(Customer, sales_order.customer)

    delivery_trip.update_sales_orders_from_db()
    assert stop.customer == sales_order.customer
    assert stop.address == customer.address
    assert stop.phone == customer.phone
    assert stop.pending_amount == sales_order.pending_amount
    assert stop.city == customer.city
    assert stop.delivery_type == services_resp["delivery_type"]
    assert bool(stop.installation) == services_resp["installation"]


def test_get_weight_non_zero(delivery_trip: DeliveryTrip, sales_order: SalesOrder):
    sales_order.total_weight = 1500
    sales_order.db_update()

    doc = new_doc(SalesOrder)
    doc.__newname = "test"  # type: ignore
    doc.set_new_name()
    doc.total_weight = 1000
    doc.db_insert()

    delivery_trip.append("stops", {"sales_order": doc.name})

    delivery_trip._get_weight()
    assert delivery_trip.weight == 2500


def test_get_weight_is_zero(delivery_trip: DeliveryTrip, sales_order: SalesOrder):
    sales_order.total_weight = 0
    sales_order.db_update()
    delivery_trip._get_weight()
    assert delivery_trip.weight == 0.0


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


def test_validate_orders_have_delivery_services_raises_on_no_delivery(
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

    delivery_trip.update_sales_orders_from_db()
    with pytest.raises(
        frappe.ValidationError,
        match=f"Sales Order {sales_order.name} has no delivery service",
    ):
        delivery_trip._validate_orders_have_delivery_services()


def test_get_template_context(delivery_trip: DeliveryTrip):
    delivery_trip.set_new_name()
    delivery_trip.update_sales_orders_from_db()
    delivery_trip._get_weight()

    context = delivery_trip._get_template_context()

    assert context["form_url"] == get_url_to_form("Delivery Trip", delivery_trip.name)
    assert context["weight"] == delivery_trip.weight
    assert context["doctype"] == "Delivery Trip"
    assert context["docname"] == delivery_trip.name

    context_stop = context["stops"][0]
    doc_stop = delivery_trip.stops[0]
    doc = get_doc(SalesOrder, doc_stop.sales_order)

    assert context_stop["customer"] == doc_stop.customer
    assert context_stop["delivery_type"] == doc_stop.delivery_type
    assert context_stop["installation"] == doc_stop.installation
    assert context_stop["phone"] == doc_stop.phone
    assert context_stop["route_url"] == _make_route_url(doc_stop.city, doc_stop.address)
    assert context_stop["address"] == doc_stop.address
    assert context_stop["pending_amount"] == doc_stop.pending_amount
    assert context_stop["details"] == doc_stop.details
    assert context_stop["items_"] == _get_items_for_order(doc)
    assert context_stop["weight"] == doc.total_weight


def test_render_telegram_message(delivery_trip: DeliveryTrip):
    delivery_trip.set_new_name()
    delivery_trip._get_weight()

    msg = delivery_trip.render_telegram_message()
    assert msg is not None
    assert "telegram_template.j2" not in msg


@pytest.mark.parametrize("insert_receipt_before", (True, False))
def test_add_receipts_to_sales_orders(
    delivery_trip: DeliveryTrip,
    sales_order: SalesOrder,
    item_no_children: Item,
    insert_receipt_before: bool,
):
    sales_order.delivery_status = "To Deliver"
    sales_order.db_update()
    doc = new_doc(SalesOrder)
    doc.name = "SO-2021-0002"
    doc.customer = sales_order.customer
    doc.append("items", {"item_code": item_no_children.item_code, "qty": 1})
    doc.services = []
    doc.validate()
    doc.delivery_status = "To Deliver"
    doc.db_insert()
    doc.db_update_all()
    if insert_receipt_before:
        doc.add_receipt()

    delivery_trip.append("stops", {"sales_order": doc.name})
    delivery_trip._add_receipts_to_sales_orders()
    assert doc_exists({"doctype": "Receipt", "voucher_no": sales_order.name})
    assert doc_exists({"doctype": "Receipt", "voucher_no": doc.name})


def test_set_completed_status(delivery_trip: DeliveryTrip):
    delivery_trip.status = "Draft"
    for stop in delivery_trip.stops:
        frappe.db.set_value(
            "Sales Order", stop.sales_order, "delivery_status", "To Deliver"
        )
    delivery_trip.set_completed_status()
    assert delivery_trip.status == "Completed"


@pytest.mark.parametrize(
    ("city", "address", "exp_url"),
    (
        ("Moscow", "Arbat, 1", "Moscow+Arbat%2C+1"),
        (None, "Arbat, 1", "Arbat%2C+1"),
        ("Moscow", None, "Moscow"),
    ),
)
def test_make_route_url_str(city: str, address: str, exp_url: str):
    base_url = "https://yandex.ru/maps/10849/severodvinsk/?text="
    assert _make_route_url(city, address) == base_url + exp_url


def test_make_route_url_none():
    assert _make_route_url(None, None) == None


delivery_and_and_installation_test_data = (
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
)


@pytest.mark.parametrize(
    ("services", "expected_result"), delivery_and_and_installation_test_data
)
def test_get_delivery_and_installation_from_services(
    services: list[dict[str, str | int]], expected_result: dict[str, str | bool]
):
    assert (
        _get_delivery_and_installation_from_services(
            [SimpleNamespace(**s) for s in services]  # type: ignore
        )
        == expected_result
    )


@pytest.mark.parametrize(
    ("services", "expected_result"), delivery_and_and_installation_test_data
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
