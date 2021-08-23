from __future__ import annotations

import json
import re
from datetime import datetime
from typing import Any, Literal, ValuesView

import frappe
from comfort import ValidationError, count_quantity, group_by_key, maybe_json
from comfort.comfort_core.ikea import add_items_to_cart, get_delivery_services
from comfort.entities.doctype.child_item.child_item import ChildItem
from comfort.finance import create_payment
from comfort.stock import create_receipt, create_stock_entry
from comfort.transactions.doctype.sales_order.sales_order import SalesOrder
from comfort.transactions.doctype.sales_order_child_item.sales_order_child_item import (
    SalesOrderChildItem,
)
from comfort.transactions.doctype.sales_order_item.sales_order_item import (
    SalesOrderItem,
)
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

# TODO: Check if there any IkeaCarts that contains those Sales Orders


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

    def delete_sales_order_dublicates(self):
        sales_orders_grouped_by_name: ValuesView[
            list[PurchaseOrderSalesOrder]
        ] = group_by_key(self.sales_orders, "sales_order_name").values()
        final_orders: list[PurchaseOrderSalesOrder] = []
        for orders in sales_orders_grouped_by_name:
            final_orders.append(orders[0])

        self.sales_orders = final_orders

    def update_sales_orders_from_db(self):
        for order in self.sales_orders:
            customer_and_total: tuple[str, int] = frappe.get_value(
                "Sales Order", order.sales_order_name, ("customer", "total_amount")
            )
            order.customer, order.total = customer_and_total

    def update_items_to_sell_from_db(self):
        for item in self.items_to_sell:
            item_values: tuple[str, int, float] = frappe.get_value(
                "Item", item.item_code, ("item_name", "rate", "weight")
            )
            item.item_name, item.rate, item.weight = item_values
            item.amount = item.qty * item.rate  # TODO: Cover

    def _calculate_items_to_sell_cost(self):
        self.items_to_sell_cost = sum(item.amount for item in self.items_to_sell)

    def _calculate_sales_orders_cost(self):
        res: list[int] = frappe.get_all(
            "Sales Order Item",
            fields=["SUM(qty * rate) AS sales_orders_cost"],
            filters={
                "parent": ("in", (ord.sales_order_name for ord in self.sales_orders))
            },
            as_list=True,
        )
        self.sales_orders_cost = res[0][0] or 0

    def _calculate_total_weight(self):
        res: list[float] = frappe.get_all(
            "Sales Order Item",
            fields=["SUM(total_weight) AS total_weight"],
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
            fields=["parent", "item_code", "qty"],
            filters={"parent": ("in", (item.item_code for item in self.items_to_sell))},
        )
        parents = (child.parent for child in child_items)
        items_to_sell = [
            item for item in self.items_to_sell.copy() if item.item_code not in parents
        ]

        return items_to_sell + child_items

    def _get_items_in_sales_orders(self, split_combinations: bool):
        if not self.sales_orders:
            return []

        items: list[SalesOrderItem | SalesOrderChildItem] = []

        sales_order_names = (ord.sales_order_name for ord in self.sales_orders)
        so_items: list[SalesOrderItem] = frappe.get_all(
            "Sales Order Item",
            fields=["item_code", "qty"],
            filters={"parent": ("in", sales_order_names)},
        )

        if split_combinations:
            child_items: list[SalesOrderChildItem] = frappe.get_all(
                "Sales Order Child Item",
                fields=["parent_item_code", "item_code", "qty"],
                filters={"parent": ("in", sales_order_names)},
            )
            items += child_items

            parents = (child.parent_item_code for child in child_items)
            so_items = [item for item in so_items if item.item_code not in parents]

        items += so_items
        return items

    def _get_templated_items_for_api(self, split_combinations: bool):
        items: list[
            PurchaseOrderItemToSell | ChildItem | SalesOrderItem | SalesOrderChildItem
        ] = self._get_items_to_sell(
            split_combinations
        ) + self._get_items_in_sales_orders(
            split_combinations
        )

        return count_quantity(items)

    def get_delivery_services(self):
        templated_items = self._get_templated_items_for_api(split_combinations=True)
        delivery_services: dict[Any, Any] = get_delivery_services(templated_items)
        self.update(
            {
                "delivery_options": delivery_services["delivery_options"],
                "cannot_add_items": json.dumps(delivery_services["cannot_add_items"]),
            }
        )

    def submit_sales_orders_and_update_statuses(self):  # pragma: no cover
        for s in self.sales_orders:
            doc: SalesOrder = frappe.get_doc("Sales Order", s.sales_order_name)
            doc.set_statuses()
            doc.submit()

    def create_stock_entries_for_purchased(self):
        create_stock_entry(
            self.doctype,
            self.name,
            "Reserved Purchased",
            self._get_items_in_sales_orders(True),
        )
        create_stock_entry(
            self.doctype,
            self.name,
            "Available Purchased",
            self._get_items_to_sell(True),
        )

    def create_payment(self):
        create_payment(self.doctype, self.name, self.total_amount, paid_with_cash=True)


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
        self.delete_sales_order_dublicates()
        self.update_sales_orders_from_db()
        self.update_items_to_sell_from_db()
        self.calculate()

    def before_insert(self):
        self.status = "Draft"

    # def before_save(self):
    #     if self.docstatus == 0:
    #         self.get_delivery_services()

    def before_submit(self):
        self.delivery_options = []
        self.cannot_add_items = None
        self.status = "To Receive"

    def on_submit(self):  # pragma: no cover
        self.create_payment()
        self.create_stock_entries_for_purchased()
        self.submit_sales_orders_and_update_statuses()

    def on_cancel(self):  # pragma: no cover
        self.submit_sales_orders_and_update_statuses()

    @frappe.whitelist()
    def add_purchase_info_and_submit(
        self,
        purchase_id: str,
        purchase_info_loaded: bool,
        purchase_info: dict[str, Any],
        delivery_cost: int = 0,
    ):

        if purchase_info_loaded:
            self.schedule_date: datetime = getdate(purchase_info["delivery_date"])
            self.posting_date: datetime = getdate(purchase_info["purchase_date"])
            self.delivery_cost = purchase_info["delivery_cost"]
        else:
            self.schedule_date: datetime = add_to_date(None, weeks=2)
            self.posting_date: datetime = today()
            self.delivery_cost = delivery_cost

        self.order_confirmation_no = purchase_id
        self.submit()

    @frappe.whitelist()
    def checkout(self):  # pragma: no cover
        items = self._get_templated_items_for_api(False)
        add_items_to_cart(items, authorize=True)

    @frappe.whitelist()
    def create_receipt(self):  # pragma: no cover
        create_receipt(self.doctype, self.name)
        self.status = "Completed"  # type: ignore
        self.db_update()


@frappe.whitelist()
def get_unavailable_items_in_cart_by_orders(
    unavailable_items: list[dict[str, Any]],
    sales_order_names: list[str],
    items_to_sell: list[dict[str, Any]],
):
    unavailable_items = maybe_json(unavailable_items)
    sales_order_names = maybe_json(sales_order_names)
    items_to_sell = maybe_json(items_to_sell)

    unavailable_item_code_to_qtys: dict[str, Any] = {}
    for item in unavailable_items:
        key = item["item_code"]
        cur_item = unavailable_item_code_to_qtys[key]
        if key in unavailable_item_code_to_qtys:
            cur_item["required_qty"] += item["required_qty"]
            cur_item["available_qty"] += item["available_qty"]
        else:
            cur_item = item

    so_items = []
    for d in ("Sales Order Item", "Sales Order Child Item"):
        so_items += frappe.get_all(
            d,
            ["item_code", "item_name", "qty", "parent"],
            {
                "parent": ("in", sales_order_names),
                "item_code": ("in", list(unavailable_item_code_to_qtys.keys())),
            },
            order_by="modified desc",
        )

    item_names: dict[str, str] = frappe.get_all(
        "Item",
        ["item_code", "item_name"],
        {"item_code": ["in", [d["item_code"] for d in items_to_sell]]},
    )

    item_names_map: dict[str, str] = {}
    for d in item_names:
        item_names_map[d["item_code"]] = d["item_name"]

    for d in items_to_sell:
        d["parent"] = ""
        d["item_name"] = item_names_map[d["item_code"]]

    res: list[dict[str, Any]] = []
    unallocated_items: dict[Any, Any] = unavailable_item_code_to_qtys
    for d in so_items + items_to_sell:
        if not d["item_code"] in unallocated_items:
            continue
        unavailable_item = unallocated_items[d["item_code"]]
        unavailable_item["required_qty"] -= d["qty"]
        available_qty = 0
        if unavailable_item["available_qty"] > 0:
            available_qty = unavailable_item["available_qty"]
            if d["qty"] > available_qty:
                unavailable_item["available_qty"] = 0
            else:
                unavailable_item["available_qty"] -= d["qty"]
        if unavailable_item["required_qty"] == 0:
            del unallocated_items[d["item_code"]]
        else:
            unallocated_items[d["item_code"]] = unavailable_item
        res.append(
            {
                "item_code": d["item_code"],
                "item_name": d["item_name"],
                "required_qty": d["qty"],
                "available_qty": available_qty,
                "sales_order": d["parent"],
            }
        )

    return sorted(res, key=lambda d: d["sales_order"])


@frappe.whitelist()
@frappe.validate_and_sanitize_search_inputs
def get_sales_order_query(
    doctype: str,
    txt: str,
    searchfield: str,
    start: str,
    page_len: str,
    filters: dict[str, Any],
) -> dict[str, Any]:
    ignore_orders: list[str] = frappe.db.sql(
        "SELECT sales_order_name from `tabPurchase Order Sales Order`"
    )
    ignore_orders = [d[0] for d in ignore_orders]
    ignore_orders += filters["not in"]
    ignore_orders_cond = ""
    if len(ignore_orders) > 0:
        ignore_orders = "(" + ",".join(["'" + d + "'" for d in ignore_orders]) + ")"
        ignore_orders_cond = f"name NOT IN {ignore_orders} AND"

    searchfields: Any = frappe.get_meta("Sales Order").get_search_fields()
    if searchfield:
        searchfields = " or ".join([field + " LIKE %(txt)s" for field in searchfields])

    res: list[tuple[Any, ...]] = frappe.db.sql(  # nosec
        """
        SELECT name, customer, total_amount from `tabSales Order`
        WHERE {ignore_orders_cond}
        status NOT IN ('Closed', 'Completed', 'Cancelled')
        AND ({scond})
        ORDER BY modified DESC
        LIMIT %(start)s, %(page_len)s
        """.format(  # nosec
            scond=searchfields, ignore_orders_cond=ignore_orders_cond
        ),
        {"txt": "%%%s%%" % txt, "start": start, "page_len": page_len},
        as_list=True,
    )

    for d in res:
        d[2] = frappe.format(d[2], "Currency")
    return res


@frappe.whitelist()
def get_purchase_history():  # pragma: no cover
    from comfort.comfort_core.ikea import get_purchase_history

    return get_purchase_history()


@frappe.whitelist()
def get_purchase_info(  # pragma: no cover
    purchase_id: int, use_lite_id: bool
) -> dict[str, bool | dict[str, Any]]:
    from comfort.comfort_core.ikea import get_purchase_info

    purchase_info = get_purchase_info(purchase_id, use_lite_id)
    return {
        "purchase_info": purchase_info,
        "purchase_info_loaded": True if purchase_info else False,
    }
