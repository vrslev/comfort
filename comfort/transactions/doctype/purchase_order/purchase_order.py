from __future__ import annotations

import re
from datetime import datetime
from typing import Any, Literal, ValuesView

import frappe
from comfort import ValidationError, count_quantity, group_by_key, parse_json
from comfort.comfort_core.ikea.cart_utils import IkeaCartUtils
from comfort.entities.doctype.child_item.child_item import ChildItem
from comfort.finance.doctype.payment.payment import Payment
from comfort.stock.doctype.receipt.receipt import Receipt
from comfort.stock.doctype.stock_entry.stock_entry import StockEntry
from comfort.transactions.doctype.sales_order.sales_order import SalesOrder
from comfort.transactions.doctype.sales_order_child_item.sales_order_child_item import (
    SalesOrderChildItem,
)
from comfort.transactions.doctype.sales_order_item.sales_order_item import (
    SalesOrderItem,
)
from frappe import _, as_json
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
    sales_order_cost: int
    delivery_cost: int
    total_weight: float
    items_to_sell_cost: int
    sales_orders: list[PurchaseOrderSalesOrder]
    items_to_sell: list[PurchaseOrderItemToSell]
    status: Literal["Draft", "To Receive", "Completed", "Cancelled"]

    def validate_not_empty(self):
        if not (self.sales_orders or self.items_to_sell):
            raise ValidationError("Добавьте заказы или товары на продажу")

    def delete_sales_order_dublicates(self):
        sales_orders_grouped_by_name: ValuesView[
            list[PurchaseOrderSalesOrder]
        ] = group_by_key(self.sales_orders, "sales_order_name").values()

        final_orders: list[PurchaseOrderSalesOrder] = []
        for orders in sales_orders_grouped_by_name:
            final_orders.append(orders[0])

        self.sales_orders = final_orders

    def update_customer_and_total_in_sales_orders_from_db(self):
        for d in self.sales_orders:
            d.customer, d.total = frappe.get_value(
                "Sales Order",
                d.sales_order_name,
                ("customer", "total_amount"),
            )

    def calculate_totals(self):
        (
            self.total_weight,
            self.total_amount,
            self.sales_order_cost,
            self.items_to_sell_cost,
        ) = (0, 0, 0, 0)
        if not self.delivery_cost:
            self.delivery_cost = 0

        sales_order_cost, sales_order_weight = frappe.get_value(
            "Sales Order Item",
            filters={
                "parent": ["in", [d.sales_order_name for d in self.sales_orders]],
            },
            fieldname=[
                "SUM(amount) AS sales_order_cost",
                "SUM(total_weight) AS sales_order_weight",
            ],
            as_dict=True,
        )
        sales_order_cost: int
        sales_order_weight: int

        self.sales_order_cost = sales_order_cost
        self.total_weight = sales_order_weight

        for item in self.items_to_sell:
            self.items_to_sell_cost += item.rate * item.qty
            self.total_weight += item.weight * item.qty

        self.total_amount = (
            self.sales_order_cost + self.items_to_sell_cost + self.delivery_cost
        )

    def get_delivery_services(self):
        try:
            templated_items = self.get_templated_items_for_api(True)
            delivery_services: dict[Any, Any] = IkeaCartUtils().get_delivery_services(
                templated_items
            )
            self.update(
                {
                    "delivery_options": delivery_services["options"],
                    "cannot_add_items": as_json(delivery_services["cannot_add"]),
                }
            )
        except Exception as e:
            frappe.msgprint("\n".join([str(arg) for arg in e.args]), title=_("Error"))

    def _get_items_to_sell(self, split_combinations: bool):
        items: list[PurchaseOrderItemToSell | ChildItem] = []
        items_to_sell = self.items_to_sell.copy()

        if split_combinations:
            child_items: list[ChildItem] = frappe.get_all(
                "Child Item",
                fields=["parent", "item_code", "qty"],
                filters={
                    "parent": ("in", (item.item_code for item in self.items_to_sell))
                },
            )
            items += child_items
            parents = (child.parent for child in child_items)
            items_to_sell = [
                item for item in self.items_to_sell if item.item_code not in parents
            ]

        items += items_to_sell
        return items

    def _get_items_in_sales_orders(self, split_combinations: bool):
        items: list[SalesOrderItem | SalesOrderChildItem] = []

        sales_order_names = (d.sales_order_name for d in self.sales_orders)
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

    def get_templated_items_for_api(self, split_combinations: bool):
        items: list[
            PurchaseOrderItemToSell | SalesOrderItem | SalesOrderChildItem | ChildItem
        ] = self._get_items_to_sell(split_combinations)

        if self.sales_orders:
            items += self._get_items_in_sales_orders(split_combinations)

        return count_quantity(items)

    def update_status_in_sales_orders(self):
        for s in self.sales_orders:
            doc: SalesOrder = frappe.get_doc("Sales Order", s.sales_order_name)
            doc.set_statuses()

    def create_stock_entries_for_purchased(self):
        StockEntry.create_for(
            self.doctype,
            self.name,
            "Reserved Purchased",
            self._get_items_in_sales_orders(True),
        )
        StockEntry.create_for(
            self.doctype,
            self.name,
            "Available Purchased",
            self._get_items_to_sell(True),
        )

    def create_payment(self):
        Payment.create_for(
            self.doctype, self.name, self.total_amount, paid_with_cash=True
        )


class PurchaseOrder(PurchaseOrderMethods):
    def autoname(self):
        months = {
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
        this_month = months[now_datetime().month].title()
        carts_in_this_month: tuple[tuple[Any]] = frappe.db.sql(
            """
            SELECT name from `tabPurchase Order`
            WHERE name LIKE CONCAT(%s, '-%%')
            ORDER BY CAST(REGEXP_SUBSTR(name, '[0-9]+$') as int) DESC
            """,
            values=(this_month,),
        )

        cart_no = None
        if carts_in_this_month:
            latest_cart_name: str = carts_in_this_month[0][0]
            latest_cart_name_no_ = re.findall(r"-(\d+)", latest_cart_name)
            if len(latest_cart_name_no_) > 0:
                latest_cart_name_no = latest_cart_name_no_[0]
                cart_no = int(latest_cart_name_no) + 1

        if not cart_no:
            cart_no = 1

        self.name = f"{this_month}-{cart_no}"

    def validate(self):
        self.validate_not_empty()
        self.delete_sales_order_dublicates()
        self.update_customer_and_total_in_sales_orders_from_db()
        self.calculate_totals()

    def before_insert(self):
        self.status = "Draft"

    # def before_save(self):
    #     if self.docstatus == 0:
    #         self.get_delivery_services()

    def before_submit(self):
        self.delivery_options = []
        self.cannot_add_items = None
        self.status = "To Receive"

        for s in self.sales_orders:
            doc: SalesOrder = frappe.get_doc("Sales Order", s.sales_order_name)
            doc.submit()

    def on_submit(self):
        self.create_payment()
        self.create_stock_entries_for_purchased()
        self.update_status_in_sales_orders()

    def on_cancel(self):
        self.update_status_in_sales_orders()

    @frappe.whitelist()
    def add_purchase_info_and_submit(
        self,
        purchase_id: str,
        purchase_info_loaded: bool,
        purchase_info: dict[str, Any],
        delivery_cost: int = 0,
    ):
        if purchase_info_loaded:
            self.schedule_date = getdate(purchase_info["delivery_date"])
            self.posting_date = getdate(purchase_info["purchase_date"])
            self.delivery_cost = purchase_info["delivery_cost"]
        else:
            self.schedule_date: datetime = add_to_date(None, weeks=2)
            self.posting_date: datetime = today()
            self.delivery_cost = delivery_cost

        self.order_confirmation_no = purchase_id
        self.submit()

    @frappe.whitelist()
    def checkout(self):
        items = self.get_templated_items_for_api(False)
        return [IkeaCartUtils().add_items_to_cart_authorized(items)]

    @frappe.whitelist()
    def create_receipt(self):
        Receipt.create_for(self.doctype, self.name)
        self.status = "Completed"  # type: ignore
        self.db_update()


@frappe.whitelist()
def get_unavailable_items_in_cart_by_orders(
    unavailable_items: list[Any],
    sales_orders: list[str],
    items_to_sell: list[dict[str, Any]],
):
    unavailable_items = parse_json(unavailable_items) or unavailable_items
    sales_orders = parse_json(sales_orders) or sales_orders
    items_to_sell = parse_json(items_to_sell) or items_to_sell

    unavailable_items_map: dict[str, Any] = {}
    for d in unavailable_items:
        if d["item_code"] in unavailable_items_map:
            item = unavailable_items_map[d["item_code"]]
            item["required_qty"] += d["required_qty"]
            item["available_qty"] += d["available_qty"]
        else:
            unavailable_items_map[d["item_code"]] = d

    so_items = []
    for d in ("Sales Order Item", "Sales Order Child Item"):
        so_items += frappe.get_all(
            d,
            ["item_code", "item_name", "qty", "parent"],
            {
                "parent": ["in", sales_orders],
                "item_code": ["in", list(unavailable_items_map.keys())],
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
    unallocated_items: dict[Any, Any] = unavailable_items_map
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
def get_purchase_history():
    return IkeaCartUtils().get_purchase_history()


@frappe.whitelist()
def get_purchase_info(purchase_id: int, use_lite_id: bool) -> dict[str, Any]:
    utils = IkeaCartUtils()
    purchase_info = None
    try:
        purchase_info = utils.get_purchase_info(purchase_id, use_lite_id=use_lite_id)
    except Exception as e:
        frappe.log_error(", ".join(e.args))
    return {
        "purchase_info_loaded": True if purchase_info else False,
        "purchase_info": purchase_info,
    }
