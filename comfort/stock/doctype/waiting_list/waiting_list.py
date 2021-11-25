from __future__ import annotations

import json
from collections import Counter
from copy import copy

from ikea_api.wrappers.types import GetDeliveryServicesResponse, UnavailableItem

import frappe
from comfort import (
    TypedDocument,
    _,
    count_qty,
    counters_are_same,
    get_all,
    get_doc,
    group_by_attr,
)
from comfort.integrations.ikea import get_delivery_services
from comfort.stock.doctype.waiting_list_sales_order.waiting_list_sales_order import (
    WaitingListSalesOrder,
)
from comfort.transactions.doctype.purchase_order_sales_order.purchase_order_sales_order import (
    PurchaseOrderSalesOrder,
)
from comfort.transactions.doctype.sales_order.sales_order import SalesOrder
from comfort.transactions.doctype.sales_order_child_item.sales_order_child_item import (
    SalesOrderChildItem,
)
from comfort.transactions.doctype.sales_order_item.sales_order_item import (
    SalesOrderItem,
)


class WaitingList(TypedDocument):
    sales_orders: list[WaitingListSalesOrder]

    def _get_items(self):
        items: list[SalesOrderChildItem | SalesOrderItem] = []
        for order in self.sales_orders:
            doc = get_doc(SalesOrder, order.sales_order)
            items += doc.get_items_with_splitted_combinations()
        return items

    def _get_unavailable_items_counter(
        self,
        items: list[SalesOrderChildItem | SalesOrderItem],
        unavailable_items: list[UnavailableItem],
        cannot_add_items: list[str],
    ):
        counter = count_qty(unavailable_items, value_attr="available_qty")

        for item_code in cannot_add_items:
            counter[item_code] = 0

        item_codes = {item.item_code for item in items}
        for item_code in counter.copy():
            if item_code not in item_codes:
                del counter[item_code]

        return counter

    def _get_status_for_order(
        self,
        items: list[SalesOrderChildItem | SalesOrderItem],
        unavailable_items_counter: Counter[str],
    ):
        counter_before = count_qty(items)
        counter_after = counter_before.copy()

        for item_code in counter_after:
            if item_code in unavailable_items_counter:
                counter_after[item_code] = unavailable_items_counter[item_code]

        if counters_are_same(counter_before, counter_after):
            status = "Fully Available"
        elif any(counter_after.values()):
            status = "Partially Available"
        else:
            status = "Not Available"
        return status

    def _process_options(
        self,
        items: list[SalesOrderChildItem | SalesOrderItem],
        delivery_services: GetDeliveryServicesResponse,
    ):
        grouped_items = group_by_attr(items, "parent")
        for order in self.sales_orders:
            cur_items = grouped_items[order.sales_order]
            current_options: dict[str, tuple[dict[str, int], str]] = {}

            for option in delivery_services.delivery_options:
                counter = self._get_unavailable_items_counter(
                    cur_items,
                    option.unavailable_items,
                    delivery_services.cannot_add,
                )
                status = self._get_status_for_order(cur_items, counter)
                current_options[option.type] = dict(counter), status

            if order.current_options:
                order.last_options = copy(order.current_options)
            order.current_options = json.dumps(current_options)
            order.options_changed = order.last_options != order.current_options

    @frappe.whitelist()
    def get_delivery_services(self):
        items = self._get_items()
        resp = get_delivery_services(count_qty(items))
        if resp is None:
            return
        self._process_options(items, resp)
        self.save()

    def _show_already_in_po_message(self):
        sales_orders_in_purchase_order = get_all(
            PurchaseOrderSalesOrder,
            filters={
                "sales_order_name": ("in", (o.sales_order for o in self.sales_orders))
            },
            fields=("sales_order_name"),
        )
        if sales_orders_in_purchase_order:
            names = [o.sales_order_name for o in sales_orders_in_purchase_order]
            frappe.msgprint(
                _("Sales Orders already in Purchase Order: {}").format(", ".join(names))
            )

    def before_save(self):
        self._show_already_in_po_message()
