# type: ignore
# flake8: noqa
from __future__ import annotations

import re
from datetime import datetime
from typing import Any

import frappe
from comfort import ValidationError, count_quantity, parse_json, stock
from comfort.comfort_core.ikea.cart_utils import IkeaCartUtils
from comfort.finance import get_account, get_received_amount
from comfort.finance.doctype.gl_entry.gl_entry import GLEntry
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
from ..sales_order.sales_order import SalesOrder


class PurchaseOrderMethods(Document):
    sales_orders: list[PurchaseOrderSalesOrder]
    items_to_sell: list[PurchaseOrderItemToSell]
    items_to_sell_cost: int
    sales_order_cost: int
    delivery_cost: int
    total_weight: float
    total_amount: int
    status: str
    delivery_options: list[PurchaseOrderDeliveryOption]
    cannot_add_items: str | None
    order_confirmation_no: int
    schedule_date: datetime
    posting_date: datetime
    difference: int

    def validate_empty(self):
        if not (self.sales_orders or self.items_to_sell):
            raise ValidationError("Добавьте заказы или товары на продажу")

    def delete_sales_order_dublicates(self):
        # TODO: Check if there any IkeaCarts that contains those Sales Orders
        sales_order_names = list({s.sales_order_name for s in self.sales_orders})
        sales_orders_no_dublicates = []

        for s in self.sales_orders:
            if s.sales_order_name in sales_order_names:
                sales_orders_no_dublicates.append(s)
                sales_order_names.remove(s.sales_order_name)

        self.sales_orders = sales_orders_no_dublicates

    def set_customer_and_total_in_sales_orders(self):
        for d in self.sales_orders:
            d.customer, total, status = frappe.get_value(
                "Sales Order",
                d.sales_order_name,
                ("customer", "total_amount", "docstatus"),
            )
            d.total = total if status != 2 else 0

    def calculate_totals(self):
        (
            self.total_weight,
            self.total_amount,
            self.sales_order_cost,
            self.items_to_sell_cost,
        ) = (0, 0, 0, 0)

        so_items = frappe.get_all(
            "Sales Order Item",
            filters={
                "parent": ["in", [d.sales_order_name for d in self.sales_orders]],
                "docstatus": ["!=", 2],
            },
            fields=[
                "SUM(qty * rate) AS sales_order_cost",
                "SUM(total_weight) AS total_weight",
            ],
        )[0]

        self.sales_order_cost = (
            so_items.sales_order_cost if so_items.sales_order_cost else 0
        )
        self.total_weight = so_items.total_weight if so_items.total_weight else 0

        for d in self.items_to_sell:
            self.items_to_sell_cost += d.rate * d.qty
            self.total_weight += d.weight * d.qty

        self.total_amount = self.sales_order_cost + self.items_to_sell_cost
        if self.delivery_cost:
            self.total_amount += self.delivery_cost
        else:
            self.delivery_cost = 0

    def get_delivery_services(self):
        try:
            templated_items = self.get_templated_items_for_api(True)
            delivery_services: dict[Any, Any] = IkeaCartUtils().get_delivery_services(
                templated_items
            )
            self.update(
                {
                    "delivery_options": delivery_services["options"],
                    "cannot_add_items": as_json(delivery_services["cannot_add"])
                    if delivery_services["cannot_add"]
                    else None,
                }
            )
        except Exception as e:
            frappe.msgprint("\n".join([str(d) for d in e.args]), _("Error"))

    def get_templated_items_for_api(self, split_combinations: bool = False):
        all_items = []
        all_items += self.items_to_sell  # TODO: Check if there's product bundle

        if self.sales_orders and len(self.sales_orders) > 0:
            sales_order_names = [d.sales_order_name for d in self.sales_orders]
            so_items = frappe.db.sql(
                """
                SELECT name, item_code, qty
                FROM `tabSales Order Item`
                WHERE parent IN %(sales_orders)s
                AND qty > 0
            """,
                {"sales_orders": sales_order_names},
                as_dict=True,
            )

            if split_combinations:
                packed_items: list[dict[Any, Any]] = frappe.db.sql(
                    """
                    SELECT parent_item_code, item_code, qty
                    FROM `tabSales Order Child Item`
                    WHERE parent IN %(sales_orders)s
                    AND qty > 0
                """,
                    {"sales_orders": sales_order_names},
                    as_dict=True,
                )
                all_items: Any
                all_items += packed_items

                parent_items = [d.parent_item_code for d in packed_items]
                so_items = [d for d in so_items if d.item_code not in parent_items]

            all_items += so_items

        templated_items: Any = {}
        for d in all_items:
            d.item_code = str(d.item_code)
            if d.item_code not in templated_items:
                templated_items[d.item_code] = 0
            templated_items[d.item_code] += int(d.qty)

        return templated_items

    def make_invoice_gl_entries(self):
        already_paid_amount = -get_received_amount(self)

        if self.total_amount != already_paid_amount:
            if self.delivery_cost > 0:
                amt_to_pay = self.total_amount - already_paid_amount
                amt_without_delivery = self.sales_order_cost + self.items_to_sell_cost
                delivery_amt_paid = 0
                if amt_to_pay > amt_without_delivery:
                    delivery_amt_paid = amt_to_pay - amt_without_delivery
                    inventory_amt_paid: int = amt_without_delivery
                else:
                    inventory_amt_paid = amt_to_pay
            else:
                inventory_amt_paid = self.total_amount - already_paid_amount

            inventory_accounts: list[str] = get_account(["cash", "prepaid_inventory"])
            GLEntry.new(self, "Invoice", inventory_accounts[0], 0, inventory_amt_paid)
            GLEntry.new(self, "Invoice", inventory_accounts[1], inventory_amt_paid, 0)

            if self.delivery_cost > 0:
                delivery_accounts: list[str] = get_account(
                    ["cash", "purchase_delivery"]
                )
                # TODO: Refactor
                GLEntry.new(self, "Invoice", delivery_accounts[1], 0, delivery_amt_paid)  # type: ignore
                GLEntry.new(self, "Invoice", delivery_accounts[1], delivery_amt_paid, 0)  # type: ignore
                make_gl_entry(self, delivery_accounts[0], 0, delivery_amt_paid)  # type: ignore
                make_gl_entry(self, delivery_accounts[1], delivery_amt_paid, 0)  # type: ignore

    def update_status_in_sales_orders(self):
        for d in self.sales_orders:
            frappe.get_doc("Sales Order", d.sales_order_name).set_statuses()

    def make_delivery_gl_entries(self):
        accounts = get_account(["prepaid_inventory", "inventory"])
        make_gl_entry(
            self, accounts[0], 0, self.items_to_sell_cost + self.sales_order_cost
        )
        make_gl_entry(
            self, accounts[1], self.items_to_sell_cost + self.sales_order_cost, 0
        )


# TODO: Statuses don't change properly, especially in SO
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
        carts_in_this_month = frappe.db.sql(
            """
            SELECT name from `tabPurchase Order`
            WHERE name LIKE CONCAT(%s, '-%%')
            ORDER BY CAST(REGEXP_SUBSTR(name, '[0-9]+$') as int) DESC
            """,
            values=(this_month,),
        )

        if carts_in_this_month:
            latest_cart_name: str = carts_in_this_month[0][0]
            latest_cart_name_no_ = re.findall(r"-(\d+)", latest_cart_name)
            if len(latest_cart_name_no_) > 0:
                latest_cart_name_no = latest_cart_name_no_[0]
            cart_no = int(latest_cart_name_no) + 1  # type: ignore
        else:  # TODO: Refactor
            cart_no = 1

        self.name = f"{this_month}-{cart_no}"

    def before_insert(self):
        self.status = "Draft"

    def validate(self):
        self.validate_empty()
        self.delete_sales_order_dublicates()
        self.set_customer_and_total_in_sales_orders()
        self.calculate_totals()

    def before_save(self):
        if self.docstatus == 0:
            self.get_delivery_services()

    def before_submit(self):
        self.delivery_options = []
        self.cannot_add_items = None

    def on_submit(self):
        stock.purchase_order_purchased(self)
        self.update_status_in_sales_orders()

    def on_cancel(self):
        self.ignore_linked_doctypes = "GL Entry"  # type: ignore
        make_reverse_gl_entry(self.doctype, self.name)  # type: ignore
        self.update_status_in_sales_orders()
        # TODO: UPDATE BIN

    @frappe.whitelist()
    def before_submit_events(
        self,
        purchase_id: int,
        purchase_info_loaded: bool,
        purchase_info: dict[str, Any],
        delivery_cost: int = 0,
    ):
        self.order_confirmation_no = purchase_id

        if purchase_info_loaded:
            self.schedule_date = getdate(purchase_info["delivery_date"])
            self.posting_date = getdate(purchase_info["purchase_date"])
            self.delivery_cost = purchase_info["delivery_cost"]
            items_cost = purchase_info["items_cost"]

        else:
            self.schedule_date: datetime = add_to_date(None, weeks=2)
            self.posting_date: datetime = today()
            # TODO:
            self.delivery_cost = delivery_cost  # type: ignore
            items_cost = self.total_amount

        if len(self.sales_orders) > 0:
            for ikea_cart_so in self.sales_orders:
                sales_order = frappe.get_doc(
                    "Sales Order", ikea_cart_so.sales_order_name
                )
                sales_order.submit()

        if self.total_amount != items_cost:
            # TODO: Ideally—edit all items in Sales Orders instead of applying this mock discount
            self.difference = self.total_amount - items_cost

        self.calculate_totals()
        self.make_invoice_gl_entries()
        self.status = "To Receive"
        self.submit()

    @frappe.whitelist()
    def checkout(self):
        items = self.get_templated_items_for_api(False)
        u = IkeaCartUtils()
        return [u.add_items_to_cart_authorized(items)]

    @frappe.whitelist()
    def set_completed(self):
        self.make_delivery_gl_entries()
        stock.purchase_order_completed(self)
        self.db_set("status", "Completed")

    @frappe.whitelist()
    def create_new_sales_order_from_items_to_sell(
        self, items: dict[Any, Any], customer: str
    ):
        if self.status != "Draft":  # TODO: Change back
            # if self.status != 'To Receive':
            raise ValidationError(
                _(
                    "Cannot create Sales Order from Purchase Order's items to sell with status {}"
                ).format(self.status)
            )

        item_qty_map = count_quantity(self.items_to_sell)

        for d in items:
            d = frappe._dict(d)  # type: ignore
            if item_qty_map[d.item_code] < d.qty:
                raise ValidationError(
                    _("Cannot add more items than there is: {}").format(
                        f"{d.item_code}: {d.qty}"
                    )
                )  # TODO: Make prettier exception

        doc: SalesOrder = frappe.get_doc(
            {
                "doctype": "Sales Order",
                "customer": customer,
                "items": items,
                "from_not_received_items_to_sell": True,  # Not change
                "edit_commission": True,
            }
        )
        doc.submit()

        # TODO: Continue working. Add order to Purchase Order


@frappe.whitelist()
def get_sales_orders_containing_items(
    items_in_options: list[str], sales_orders: list[str]
) -> dict[str, list[Any]]:
    items_in_options = parse_json(items_in_options) or items_in_options
    sales_orders = parse_json(sales_orders) or items_in_options
    items_in_sales_orders_by_options = {}
    for option in items_in_options:
        items_in_sales_orders = {}
        for item in items_in_options[option]:
            sales_orders_with_item = frappe.db.get_list(
                "Sales Order",
                filters={"name": ["in", sales_orders], "item_code": ["in", [item]]},
                fields=["name"],
                as_list=True,
            )
            items_in_sales_orders[item] = [s[0] for s in sales_orders_with_item]
        items_in_sales_orders_by_options[option] = items_in_sales_orders
    return items_in_sales_orders_by_options


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

    item_names = frappe.get_all(
        "Item",
        ["item_code", "item_name"],
        {"item_code": ["in", [d["item_code"] for d in items_to_sell]]},
    )

    item_names_map = {}
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
    doctype: str, txt: str, searchfield: str, start: str, page_len: str, filters: str
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

    res = frappe.db.sql(  # nosec
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
