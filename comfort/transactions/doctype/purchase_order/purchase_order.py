from __future__ import annotations

import json
import re
from datetime import datetime
from types import SimpleNamespace
from typing import Any, Literal

import frappe
from comfort.entities import ChildItem
from comfort.finance.utils import create_payment
from comfort.integrations.ikea import (
    PurchaseInfoDict,
    add_items_to_cart,
    fetch_items,
    get_delivery_services,
)
from comfort.stock.utils import create_checkout, create_receipt
from comfort.transactions.doctype.purchase_order_delivery_option.purchase_order_delivery_option import (
    PurchaseOrderDeliveryOption,
)
from comfort.transactions.doctype.purchase_order_item_to_sell.purchase_order_item_to_sell import (
    PurchaseOrderItemToSell,
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
from comfort.transactions.utils import (
    AnyChildItem,
    delete_empty_items,
    merge_same_items,
)
from comfort.utils import (
    TypedDocument,
    ValidationError,
    _,
    count_qty,
    get_all,
    get_cached_value,
    get_doc,
    get_value,
    group_by_attr,
    maybe_json,
)


class PurchaseOrder(TypedDocument):
    doctype: Literal["Purchase Order"]

    delivery_options: list[PurchaseOrderDeliveryOption] = []
    cannot_add_items: str | None
    posting_date: datetime | None
    order_confirmation_no: str | None
    schedule_date: datetime | None
    total_amount: int
    sales_orders_cost: int
    delivery_cost: int
    total_weight: float
    total_margin: int
    items_to_sell_cost: int
    sales_orders: list[PurchaseOrderSalesOrder] = []
    items_to_sell: list[PurchaseOrderItemToSell] = []
    status: Literal["Draft", "To Receive", "Completed", "Cancelled"]
    amended_from: str | None

    #########
    # Hooks #
    #########

    def autoname(self) -> None:
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
        this_month = months_number_to_name[datetime.now().month]

        carts_in_this_month: tuple[tuple[str]] | None = frappe.db.sql(  # type: ignore
            """
            SELECT name from `tabPurchase Order`
            WHERE name LIKE CONCAT(%s, '-%%')
            ORDER BY CAST(REGEXP_SUBSTR(name, '[0-9]+$') as int) DESC
            LIMIT 1
            """,
            values=(this_month,),
        )

        if carts_in_this_month:
            matches = re.findall(r"-(\d+)", carts_in_this_month[0][0])
            new_cart_number = int(matches[0]) + 1
        else:
            new_cart_number = 1

        self.name = f"{this_month}-{new_cart_number}"

    def validate(self) -> None:
        self._validate_not_empty()
        self._delete_sales_order_duplicates()
        delete_empty_items(self, "items_to_sell")
        self.items_to_sell = merge_same_items(self.items_to_sell)
        self.update_sales_orders_from_db()
        self.update_items_to_sell_from_db()
        self.calculate()

    def before_insert(self) -> None:
        self.status = "Draft"
        self._clear_no_copy_fields_for_amended()

    def before_save(self) -> None:
        self.delivery_options = []
        self.cannot_add_items = None

    def before_submit(self) -> None:
        self.delivery_options = []
        self.cannot_add_items = None
        self.status = "To Receive"

    def on_submit(self) -> None:
        self._create_payment()
        self._create_checkout()
        self._submit_sales_orders_and_update_statuses()

    def before_cancel(self) -> None:
        self.status = "Cancelled"

    def on_cancel(self) -> None:  # pragma: no cover
        self._submit_sales_orders_and_update_statuses()

    ################
    # End of hooks #
    ################

    def _validate_not_empty(self):
        if not (self.sales_orders or self.items_to_sell):
            raise ValidationError(_("Add Sales Orders or Items to Sell"))

    def _delete_sales_order_duplicates(self) -> None:
        sales_orders_grouped_by_name = group_by_attr(
            self.sales_orders, "sales_order_name"
        ).values()
        self.sales_orders = [orders[0] for orders in sales_orders_grouped_by_name]

    def update_sales_orders_from_db(self) -> None:
        for order in self.sales_orders:
            order_values: tuple[str, int] | None = get_value(
                "Sales Order", order.sales_order_name, ("customer", "total_amount")
            )
            if order_values is not None:
                order.customer, order.total_amount = order_values

    def update_items_to_sell_from_db(self) -> None:
        for item in self.items_to_sell:
            item_values: tuple[str, int, float] = get_value(
                "Item", item.item_code, ("item_name", "rate", "weight")
            )
            item.item_name, item.rate, item.weight = item_values
            item.amount = item.qty * item.rate

    def _clear_no_copy_fields_for_amended(self) -> None:
        if not self.amended_from:
            return

        self.posting_date = None
        self.order_confirmation_no = None
        self.schedule_date = None
        self.delivery_cost = 0

    def _calculate_items_to_sell_cost(self) -> None:
        self.items_to_sell_cost = sum(item.amount for item in self.items_to_sell)

    def _calculate_sales_orders_cost(self) -> None:
        res: list[list[int]] = frappe.get_all(
            "Sales Order Item",
            fields="SUM(qty * rate) AS sales_orders_cost",
            filters={
                "parent": ("in", (o.sales_order_name for o in self.sales_orders)),
                "docstatus": ("!=", 2),
            },
            as_list=True,
        )
        self.sales_orders_cost = res[0][0] or 0

    def _calculate_total_weight(self) -> None:
        res: list[list[float]] = frappe.get_all(
            "Sales Order Item",
            fields="SUM(total_weight) AS total_weight",
            filters={
                "parent": ("in", (o.sales_order_name for o in self.sales_orders)),
                "docstatus": ("!=", 2),
            },
            as_list=True,
        )
        sales_orders_weight = res[0][0] or 0.0
        items_to_sell_weight = sum(
            item.weight * item.qty
            for item in self.items_to_sell
            if item.weight and item.qty
        )
        self.total_weight = sales_orders_weight + items_to_sell_weight

    def _calculate_total_amount(self) -> None:
        if not self.delivery_cost:
            self.delivery_cost = 0
        if not self.items_to_sell_cost:
            self.items_to_sell_cost = 0
        if not self.sales_orders_cost:
            self.sales_orders_cost = 0

        self.total_amount = (
            self.sales_orders_cost + self.items_to_sell_cost + self.delivery_cost
        )

    def _calculate_total_margin(self) -> None:
        self.total_margin = (
            get_all(
                SalesOrder,
                filter={
                    "name": ("in", (o.sales_order_name for o in self.sales_orders)),
                    "docstatus": ("!=", 2),
                },
                field="SUM(margin) as margin",
            )[0].margin
            or 0
        )

    def calculate(self) -> None:
        self._calculate_items_to_sell_cost()
        self._calculate_sales_orders_cost()
        self._calculate_total_weight()
        self._calculate_total_amount()
        self._calculate_total_margin()

    def get_items_to_sell(
        self, split_combinations: bool
    ) -> list[PurchaseOrderItemToSell | ChildItem]:
        res: list[PurchaseOrderItemToSell | ChildItem] = []
        if not self.items_to_sell:
            return res

        if not split_combinations:
            res += self.items_to_sell
            return res

        child_items = get_all(
            ChildItem,
            field=("parent", "item_code", "qty"),
            filter={"parent": ("in", (i.item_code for i in self.items_to_sell))},
        )

        # If item to sell has child items, they are accounted wrong.
        # now: {'39331867': 4} => {'30469171': 1, '10406797': 1}
        # should be: {'39331867': 4} => {'30469171': 4, '10406797': 4}
        parent_counter = count_qty(self.items_to_sell)
        for child in child_items:
            child.qty = child.qty * parent_counter[child.parent]

        parents = {child.parent for child in child_items}
        items_to_sell = (i for i in self.items_to_sell if i.item_code not in parents)

        res += items_to_sell
        res += child_items
        return res

    def get_items_in_sales_orders(self, split_combinations: bool):
        items: list[SalesOrderItem | SalesOrderChildItem] = []
        if not self.sales_orders:
            return items

        sales_order_names = [o.sales_order_name for o in self.sales_orders]
        so_items = get_all(
            SalesOrderItem,
            field=("item_code", "qty"),
            filter={"parent": ("in", sales_order_names), "docstatus": ("!=", 2)},
        )

        if split_combinations:
            child_items = get_all(
                SalesOrderChildItem,
                field=("parent_item_code", "item_code", "qty"),
                filter={"parent": ("in", sales_order_names), "docstatus": ("!=", 2)},
            )
            items += child_items

            parents = [child.parent_item_code for child in child_items]
            so_items = [item for item in so_items if item.item_code not in parents]

        items += so_items
        return items

    def _get_templated_items_for_api(self, split_combinations: bool):
        items: list[AnyChildItem] = list(self.get_items_to_sell(split_combinations))
        items += self.get_items_in_sales_orders(split_combinations)
        return count_qty(items)

    @frappe.whitelist()
    def get_delivery_services(self) -> None:
        templated_items = self._get_templated_items_for_api(split_combinations=True)
        response = get_delivery_services(templated_items)
        if not response:
            return

        self.cannot_add_items = json.dumps(response.cannot_add)
        self.delivery_options = []
        for option in response.delivery_options:
            self.append(
                "delivery_options",
                {
                    "is_available": option.is_available,
                    "type": option.type,
                    "service_provider": option.service_provider,
                    "date": option.date,
                    "price": option.price,
                    "unavailable_items": json.dumps(
                        [o.dict() for o in option.unavailable_items]
                    ),
                },
            )
        self.save_without_validating()

    def _submit_sales_orders_and_update_statuses(self) -> None:
        for o in self.sales_orders:
            doc = get_doc(SalesOrder, o.sales_order_name)
            if doc.docstatus == 2:
                continue
            doc.set_statuses()
            doc.flags.ignore_validate_update_after_submit = True
            doc.submit()

    def _create_payment(self) -> None:
        create_payment(self.doctype, self.name, self.total_amount, paid_with_cash=False)

    def _create_checkout(self) -> None:
        create_checkout(self.name)

    @frappe.whitelist()
    def fetch_items_specs(self) -> None:
        items: list[AnyChildItem] = list(self.get_items_to_sell(False))
        items += self.get_items_in_sales_orders(False)
        item_codes = [i.item_code for i in items]
        fetched_item_codes = fetch_items(item_codes, force_update=True)["successful"]

        for po_sales_order in self.sales_orders:
            sales_order = get_doc(SalesOrder, po_sales_order.sales_order_name)
            if any(i.item_code in fetched_item_codes for i in sales_order.items):
                sales_order.flags.ignore_validate_update_after_submit = True  # There may be Sales Order that are submitted from cancelled Purchase Order
                sales_order.update_items_from_db()
                sales_order.save()

        # Update Items to Sell if changed and also update Sales Orders
        self.save()

        frappe.msgprint(_("Information about items updated"), alert=True)

    @frappe.whitelist()
    def add_purchase_info_and_submit(
        self, purchase_id: str, purchase_info: PurchaseInfoDict
    ) -> None:
        # Schedule date and posting date could be not loaded
        self.schedule_date = purchase_info.get("delivery_date", datetime.now())  # type: ignore
        self.posting_date = purchase_info.get("purchase_date", datetime.now())  # type: ignore
        self.delivery_cost = int(purchase_info["delivery_cost"])
        self.order_confirmation_no = purchase_id
        self.submit()

    @frappe.whitelist()
    def checkout(self) -> None:
        add_items_to_cart(self._get_templated_items_for_api(False), authorize=True)

    @frappe.whitelist()
    def add_receipt(self) -> None:
        create_receipt(self.doctype, self.name)
        self.status = "Completed"
        self.save_without_validating()
        self._submit_sales_orders_and_update_statuses()

    @frappe.whitelist()
    def get_unavailable_items_in_cart_by_orders(
        self, unavailable_items: list[dict[str, str | int]]
    ):  # pragma: no cover
        all_items: list[Any] = []
        for order in self.sales_orders:
            doc = get_doc(SalesOrder, order.sales_order_name)
            all_items += doc.get_items_with_splitted_combinations()
        items_to_sell = self.get_items_to_sell(split_combinations=True)
        for item in items_to_sell:
            item.parent = self.name
        all_items += items_to_sell

        counter = count_qty(
            (SimpleNamespace(**i) for i in maybe_json(unavailable_items)),
            value_attr="available_qty",
        )
        grouped_items = group_by_attr(i for i in all_items if i.item_code in counter)

        res: list[dict[str, str | int | None]] = []
        for cur_items in grouped_items.values():
            for idx, item in enumerate(cur_items):
                if item.item_name is None:
                    item.item_name = get_cached_value(
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
def calculate_total_weight_and_total_weight(doc: str):
    purchase_order = PurchaseOrder(json.loads(doc))
    purchase_order._calculate_total_weight()
    purchase_order._calculate_total_margin()
    return purchase_order.total_weight, purchase_order.total_margin
