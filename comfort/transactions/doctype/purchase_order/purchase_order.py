from __future__ import annotations

import json
import re
from datetime import datetime
from typing import Any, Literal

from ikea_api_wrapped.parsers.order_capture import DeliveryOptionDict
from ikea_api_wrapped.wrappers import PurchaseInfoDict

import frappe
from comfort import ValidationError, count_qty, group_by_attr, maybe_json
from comfort.comfort_core.ikea import add_items_to_cart, get_delivery_services
from comfort.entities.doctype.child_item.child_item import ChildItem
from comfort.finance import create_payment
from comfort.stock import create_checkout, create_receipt
from comfort.transactions import AnyChildItem, delete_empty_items, merge_same_items
from frappe import _
from frappe.model.document import Document
from frappe.utils.data import add_to_date, getdate, now_datetime, today

from ..purchase_order_delivery_option.purchase_order_delivery_option import (
    PurchaseOrderDeliveryOption,
)
from ..purchase_order_item_to_sell.purchase_order_item_to_sell import (
    PurchaseOrderItemToSell,
)
from ..purchase_order_sales_order.purchase_order_sales_order import (
    PurchaseOrderSalesOrder,
)
from ..sales_order.sales_order import SalesOrder
from ..sales_order_child_item.sales_order_child_item import SalesOrderChildItem
from ..sales_order_item.sales_order_item import SalesOrderItem

# TODO: Validate that this Purchase Order is the only one that contains current Sales Orders


class PurchaseOrderMethods(Document):
    delivery_options: list[PurchaseOrderDeliveryOption]
    cannot_add_items: str | None
    posting_date: datetime
    order_confirmation_no: str
    schedule_date: datetime
    total_amount: int
    sales_orders_cost: int
    delivery_cost: int
    total_weight: float
    items_to_sell_cost: int
    sales_orders: list[PurchaseOrderSalesOrder]
    items_to_sell: list[PurchaseOrderItemToSell]
    status: Literal["Draft", "To Receive", "Completed", "Cancelled"]

    def validate_not_empty(self):
        if not (self.sales_orders or self.items_to_sell):
            raise ValidationError(_("Add Sales Orders or Items to Sell"))

    def delete_sales_order_duplicates(self):
        sales_orders_grouped_by_name = group_by_attr(
            self.sales_orders, "sales_order_name"
        ).values()
        self.sales_orders = [orders[0] for orders in sales_orders_grouped_by_name]

    def update_sales_orders_from_db(self):
        for order in self.sales_orders:
            order_values: tuple[str, int] = frappe.get_value(
                "Sales Order", order.sales_order_name, ("customer", "total_amount")
            )
            order.customer, order.total_amount = order_values

    def update_items_to_sell_from_db(self):
        for item in self.items_to_sell:
            item_values: tuple[str, int, float] = frappe.get_value(
                "Item", item.item_code, ("item_name", "rate", "weight")
            )
            item.item_name, item.rate, item.weight = item_values
            item.amount = item.qty * item.rate

    def _calculate_items_to_sell_cost(self):
        self.items_to_sell_cost = sum(item.amount for item in self.items_to_sell)

    def _calculate_sales_orders_cost(self):
        res: list[int] = frappe.get_all(
            "Sales Order Item",
            fields="SUM(qty * rate) AS sales_orders_cost",
            filters={
                "parent": ("in", (ord.sales_order_name for ord in self.sales_orders))
            },
            as_list=True,
        )
        self.sales_orders_cost = res[0][0] or 0

    @frappe.whitelist()
    def _calculate_total_weight(self):
        res: list[float] = frappe.get_all(
            "Sales Order Item",
            fields="SUM(total_weight) AS total_weight",
            filters={
                "parent": ("in", (ord.sales_order_name for ord in self.sales_orders))
            },
            as_list=True,
        )
        sales_orders_weight = res[0][0] or 0.0
        items_to_sell_weight = sum(
            item.weight * item.qty for item in self.items_to_sell
        )
        self.total_weight = sales_orders_weight + items_to_sell_weight

    def _calculate_total_amount(self):
        if not self.delivery_cost:
            self.delivery_cost = 0
        if not self.items_to_sell_cost:
            self.items_to_sell_cost = 0
        if not self.sales_orders_cost:
            self.sales_orders_cost = 0

        self.total_amount = (
            self.sales_orders_cost + self.items_to_sell_cost + self.delivery_cost
        )

    def calculate(self):  # pragma: no cover
        self._calculate_items_to_sell_cost()
        self._calculate_sales_orders_cost()
        self._calculate_total_weight()
        self._calculate_total_amount()

    def _get_items_to_sell(
        self, split_combinations: bool
    ) -> list[PurchaseOrderItemToSell | ChildItem]:
        if not self.items_to_sell:
            return []
        if not split_combinations:
            return self.items_to_sell

        child_items: list[ChildItem] = frappe.get_all(
            "Child Item",
            fields=("parent", "item_code", "qty"),
            filters={"parent": ("in", (i.item_code for i in self.items_to_sell))},
        )
        parents = [child.parent for child in child_items]
        items_to_sell = [
            item for item in self.items_to_sell if item.item_code not in parents
        ]
        return items_to_sell + child_items

    def _get_items_in_sales_orders(self, split_combinations: bool):
        if not self.sales_orders:
            return []

        sales_order_names = [ord.sales_order_name for ord in self.sales_orders]
        so_items: list[SalesOrderItem] = frappe.get_all(
            "Sales Order Item",
            fields=("item_code", "qty"),
            filters={"parent": ("in", sales_order_names)},
        )

        items: list[SalesOrderItem | SalesOrderChildItem] = []

        if split_combinations:
            child_items: list[SalesOrderChildItem] = frappe.get_all(
                "Sales Order Child Item",
                fields=("parent_item_code", "item_code", "qty"),
                filters={"parent": ("in", sales_order_names)},
            )
            items += child_items

            parents = [child.parent_item_code for child in child_items]
            so_items = [item for item in so_items if item.item_code not in parents]

        items += so_items
        return items

    def _get_templated_items_for_api(self, split_combinations: bool):
        items: list[AnyChildItem] = self._get_items_to_sell(
            split_combinations
        ) + self._get_items_in_sales_orders(split_combinations)
        return count_qty(items)

    def _clear_delivery_options(self):
        for option in self.delivery_options:
            frappe.delete_doc(option.doctype, option.name)
        self.delivery_options = []

    @frappe.whitelist()
    def get_delivery_services(self):
        self._clear_delivery_options()

        templated_items = self._get_templated_items_for_api(split_combinations=True)
        response = get_delivery_services(templated_items)
        if not response:
            return

        options: list[DeliveryOptionDict] = response["delivery_options"]
        self.cannot_add_items = json.dumps(response["cannot_add"])
        for option in options:
            self.append(
                "delivery_options",
                {
                    "type": option["delivery_type"],
                    "service_provider": option["service_provider"],
                    "date": option["delivery_date"],
                    "price": option["price"],
                    "unavailable_items": json.dumps(option["unavailable_items"]),
                },
            )
        self.db_update_all()

    def submit_sales_orders_and_update_statuses(self):  # pragma: no cover
        for ord in self.sales_orders:
            doc: SalesOrder = frappe.get_doc("Sales Order", ord.sales_order_name)
            doc.set_statuses()
            doc.flags.ignore_validate_update_after_submit = True
            doc.submit()

    def create_payment(self):
        create_payment(self.doctype, self.name, self.total_amount, paid_with_cash=False)

    def create_checkout(self):  # pragma: no cover
        create_checkout(self.name)


class PurchaseOrder(PurchaseOrderMethods):
    def autoname(self):
        months_number_to_name = {
            1: "Январь",
            2: "Февраль",
            3: "Март",
            4: "Апрель",
            5: "Май",
            6: "Июнь",
            7: "Июль",
            8: "Август",
            9: "Сентябрь",
            10: "Октябрь",
            11: "Ноябрь",
            12: "Декабрь",
        }
        this_month = months_number_to_name[now_datetime().month]

        carts_in_this_month: tuple[tuple[str | None]] = frappe.db.sql(
            """
            SELECT name from `tabPurchase Order`
            WHERE name LIKE CONCAT(%s, '-%%')
            ORDER BY CAST(REGEXP_SUBSTR(name, '[0-9]+$') as int) DESC
            LIMIT 1
            """,
            values=(this_month,),
        )

        new_cart_number: int = 1
        if carts_in_this_month:
            matches = re.findall(r"-(\d+)", carts_in_this_month[0][0])
            latest_cart_number: str | int = matches[0] if matches else 0
            new_cart_number = int(latest_cart_number) + 1

        self.name = f"{this_month}-{new_cart_number}"

    def validate(self):  # pragma: no cover
        self.validate_not_empty()
        self.delete_sales_order_duplicates()
        delete_empty_items(self, "items_to_sell")
        self.items_to_sell = merge_same_items(self.items_to_sell)
        self.update_sales_orders_from_db()
        self.update_items_to_sell_from_db()
        self.calculate()

    def before_insert(self):
        self.status = "Draft"

    def before_save(self):
        self.delivery_options = []
        self.cannot_add_items = None

    def before_submit(self):
        self.delivery_options = []
        self.cannot_add_items = None
        self.status = "To Receive"

    def on_submit(self):  # pragma: no cover
        self.create_payment()
        self.create_checkout()
        self.submit_sales_orders_and_update_statuses()

    def on_cancel(self):  # pragma: no cover
        self.submit_sales_orders_and_update_statuses()

    @frappe.whitelist()
    def add_purchase_info_and_submit(
        self, purchase_id: str, purchase_info: PurchaseInfoDict
    ):
        self.schedule_date = getdate(
            purchase_info.get("delivery_date", add_to_date(None, weeks=2))
        )
        self.posting_date = getdate(purchase_info.get("purchase_date", today()))
        self.delivery_cost = int(purchase_info["delivery_cost"])
        self.order_confirmation_no = purchase_id
        self.submit()

    @frappe.whitelist()
    def checkout(self):  # pragma: no cover
        add_items_to_cart(self._get_templated_items_for_api(False), authorize=True)

    @frappe.whitelist()
    def add_receipt(self):  # pragma: no cover
        create_receipt(self.doctype, self.name)
        self.status = "Completed"
        self.db_update()
        self.submit_sales_orders_and_update_statuses()

    @frappe.whitelist()
    def get_unavailable_items_in_cart_by_orders(  # TODO: It renders with duplicates
        self, unavailable_items: list[dict[str, str | int]]
    ):  # pragma: no cover
        all_items: list[AnyChildItem] = []
        for order in self.sales_orders:
            doc: SalesOrder = frappe.get_doc("Sales Order", order.sales_order_name)
            all_items += doc._get_items_with_splitted_combinations()
        items_to_sell = self._get_items_to_sell(split_combinations=True)
        for item in items_to_sell:
            item.parent = self.name
        all_items += items_to_sell

        counter = count_qty(
            (frappe._dict(i) for i in maybe_json(unavailable_items)),
            value_attr="available_qty",
        )
        grouped_items = group_by_attr(i for i in all_items if i.item_code in counter)

        res: list[dict[str, str | int | None]] = []
        for cur_items in grouped_items.values():
            for idx, item in enumerate(cur_items):
                if item.item_name is None:
                    item.item_name = frappe.get_cached_value(
                        "Item", item.item_code, "item_name"
                    )
                res.append(
                    {
                        "item_code": item.item_code if idx == 0 else None,
                        "item_name": item.item_name if idx == 0 else None,
                        "required_qty": item.qty,
                        "available_qty": counter[item.item_code] if idx == 0 else None,
                        "parent": item.parent,
                    }
                )
        return res or None


@frappe.whitelist()
@frappe.validate_and_sanitize_search_inputs  # pragma: no cover
def sales_order_query(
    doctype: str,
    txt: str,
    searchfield: str,
    start: str,
    page_len: str,
    filters: dict[str, Any],
) -> dict[str, Any]:
    ignore_orders: list[str] = [
        s.sales_order_name
        for s in frappe.get_all(
            "Purchase Order Sales Order",
            "sales_order_name",
            {"parent": ("!=", filters["docname"])},
        )
    ] + filters["not in"]

    ignore_orders_cond = ""
    if len(ignore_orders) > 0:
        ignore_orders = "(" + ",".join(f"'{d}'" for d in ignore_orders) + ")"
        ignore_orders_cond = f"name NOT IN {ignore_orders} AND"

    searchfields: list[Any] = frappe.get_meta("Sales Order").get_search_fields()
    if searchfield:
        searchfields = " or ".join(field + " LIKE %(txt)s" for field in searchfields)

    orders: list[tuple[Any, ...]] = frappe.db.sql(  # nosec
        """
        SELECT name, customer, total_amount from `tabSales Order`
        WHERE {ignore_orders_cond}
        status NOT IN ('Closed', 'Completed', 'Cancelled')
        AND ({scond})
        ORDER BY modified DESC
        LIMIT %(start)s, %(page_len)s
        """.format(
            scond=searchfields, ignore_orders_cond=ignore_orders_cond
        ),
        {"txt": "%%%s%%" % txt, "start": start, "page_len": page_len},
        as_list=True,
    )

    for order in orders:
        order[2] = frappe.format(order[2], "Currency")
    return orders
