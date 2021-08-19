from __future__ import annotations

# TODO: Allow change services on submit
from typing import Any, Generator, Iterable, Literal

import frappe
from comfort import ValidationError, count_quantity, group_by_key
from comfort.comfort_core.doctype.commission_settings.commission_settings import (
    CommissionSettings,
)
from comfort.entities.doctype.child_item.child_item import ChildItem
from comfort.entities.doctype.item.item import Item
from comfort.finance import create_payment, get_received_amount
from comfort.stock import create_receipt
from frappe import _
from frappe.model.document import Document

from ..sales_order_child_item.sales_order_child_item import SalesOrderChildItem
from ..sales_order_item.sales_order_item import SalesOrderItem
from ..sales_order_service.sales_order_service import SalesOrderService


class SalesOrderMethods(Document):
    customer: str
    items: list[SalesOrderItem]
    services: list[SalesOrderService]
    commission: int
    edit_commission: bool
    discount: int
    total_amount: int
    paid_amount: int
    pending_amount: int
    total_quantity: int
    items_cost: int
    service_amount: int
    total_weight: float
    margin: int
    child_items: list[SalesOrderChildItem]
    status: Literal["Draft", "In Progress", "Completed", "Cancelled"]
    payment_status: Literal["", "Unpaid", "Partially Paid", "Paid", "Overpaid"]
    per_paid: float
    delivery_status: Literal["To Purchase", "Purchased", "To Deliver", "Delivered"]

    def merge_same_items(self):
        """Merge items that have same Item Code."""
        items_grouped_by_item_code: Iterable[list[SalesOrderItem]] = group_by_key(
            self.items
        ).values()
        final_items: list[SalesOrderItem] = []

        for cur_items in items_grouped_by_item_code:
            if len(cur_items) > 1:
                full_qty = list(count_quantity(cur_items).values())[0]
                cur_items[0].qty = full_qty

            final_items.append(cur_items[0])

        self.items = final_items

    def delete_empty_items(self):
        """Delete items that have zero quantity."""
        to_remove: Generator[SalesOrderItem, None, None] = (
            item for item in self.items if item.qty == 0
        )
        for item in to_remove:
            self.items.remove(item)

    def update_items_from_db(self):
        """Load item properties from database and calculate Amount and Total Weight."""
        for item in self.items:
            doc: Item = frappe.get_cached_doc("Item", item.item_code)
            item.item_name = doc.item_name
            item.rate = doc.rate
            item.weight = doc.weight

            item.amount = item.rate * item.qty
            item.total_weight = item.weight * item.qty

    def set_child_items(self):
        """Generate Child Items from combinations in Items."""

        self.child_items = []
        if not self.items:
            return

        child_items: list[ChildItem] = frappe.get_all(
            "Child Item",
            fields=("parent", "item_code", "item_name", "qty"),
            filters={"parent": ("in", (d.item_code for d in self.items))},
        )

        item_codes_to_qty = count_quantity(self.items)
        for d in child_items:
            d.qty = d.qty * item_codes_to_qty[d.parent]

        self.extend("child_items", child_items)

    def _calculate_item_totals(self):
        """Calculate global Total Quantity, Weight and Items Cost."""
        self.total_quantity, self.total_weight, self.items_cost = 0, 0.0, 0
        for item in self.items:
            self.total_quantity += item.qty
            self.total_weight += item.total_weight
            self.items_cost += item.amount

    def _calculate_service_amount(self):
        self.service_amount = sum(s.rate for s in self.services)

    def _calculate_commission(self):
        """Calculate commission based rules set in Commission Settings if `edit_commission` is False."""
        if not self.edit_commission:
            self.commission = CommissionSettings.get_commission_percentage(
                self.items_cost
            )

    def _calculate_margin(self):
        """Calculate margin based on commission and rounding remainder of items_cost."""
        if self.items_cost <= 0:
            self.margin = 0
            return

        base_margin = self.items_cost * self.commission / 100
        items_cost_rounding_remainder = round(self.items_cost, -1) - self.items_cost
        rounded_margin = int(round(base_margin, -1) + items_cost_rounding_remainder)
        self.margin = rounded_margin

    def _calculate_total_amount(self):
        self.total_amount = (
            self.items_cost + self.margin + self.service_amount - self.discount
        )

    def calculate(self):  # pragma: no cover
        """Calculate all things that are calculable."""
        self._calculate_item_totals()
        self._calculate_service_amount()
        self._calculate_commission()
        self._calculate_margin()
        self._calculate_total_amount()


class SalesOrderStatuses(SalesOrderMethods):
    def _set_paid_and_pending_per_amount(self):
        self.paid_amount = get_received_amount(self)

        if self.total_amount == 0:
            self.per_paid = 100
        else:
            self.per_paid = self.paid_amount / self.total_amount * 100

        self.pending_amount = self.total_amount - self.paid_amount

    def _set_payment_status(self):
        if self.docstatus == 2:
            status = ""
        elif self.per_paid > 100:
            status = "Overpaid"
        elif self.per_paid == 100:
            status = "Paid"
        elif self.per_paid > 0:
            status = "Partially Paid"
        else:
            status = "Unpaid"

        self.payment_status = status  # type: ignore

    def _set_delivery_status(self):
        if self.docstatus == 2:
            status = ""
        elif frappe.db.exists(
            "Receipt",
            {"voucher_type": self.doctype, "voucher_no": self.name, "docstatus": 1},
        ):
            status = "Delivered"
        else:
            purchase_order_name: str | None
            if purchase_order_name := frappe.get_value(
                "Purchase Order Sales Order",
                fieldname="parent",
                filters={"sales_order_name": self.name, "docstatus": 1},
            ):
                if frappe.db.exists(
                    "Receipt",
                    {
                        "voucher_type": "Purchase Order",
                        "voucher_no": purchase_order_name,
                        "docstatus": 1,
                    },
                ):
                    status = "To Deliver"
                else:
                    status = "Purchased"
            else:
                status = "To Purchase"

        self.delivery_status = status  # type: ignore

    def _set_document_status(self):
        """Set Document Status. Depends on `docstatus`, `payment_status` and `delivery_status`."""
        if self.docstatus == 0:
            status = "Draft"
        elif self.docstatus == 1:
            if self.payment_status == "Paid" and self.delivery_status == "Delivered":
                status = "Completed"
            else:
                status = "In Progress"
        else:
            status = "Cancelled"

        self.status = status  # type: ignore

    def set_statuses(self):  # pragma: no cover
        """Set statuses according to current Sales Order and linked Purchase Order states."""
        self._set_paid_and_pending_per_amount()
        self._set_payment_status()
        self._set_delivery_status()
        self._set_document_status()


class SalesOrder(SalesOrderStatuses):
    def validate(self):  # pragma: no cover
        self.delete_empty_items()
        self.merge_same_items()
        self.update_items_from_db()
        self.set_child_items()

        self.calculate()
        self.set_statuses()

    def before_submit(self):  # pragma: no cover
        self.edit_commission = True

    def before_cancel(self):  # pragma: no cover
        self.set_statuses()

    def before_update_after_submit(self):  # pragma: no cover
        self.calculate()
        self.set_statuses()

    @frappe.whitelist()
    def calculate_commission_and_margin(self):  # pragma: no cover
        self._calculate_commission()
        self._calculate_margin()

    @frappe.whitelist()
    def add_payment(self, paid_amount: int, cash: bool):  # pragma: no cover
        create_payment(self.doctype, self.name, paid_amount, cash)
        self.set_statuses()
        self.db_update()

    @frappe.whitelist()
    def add_receipt(self):
        if self.delivery_status == "Delivered":
            raise ValidationError(
                _('Delivery Status of this Sales Order is already "Delivered"')
            )

        create_receipt(self.doctype, self.name)
        self.set_statuses()
        self.db_update()

    @frappe.whitelist()
    def split_combinations(self, combos_to_split: list[str], save: bool):
        """Split all combinations in Items."""
        combos_to_split = list(set(combos_to_split))

        selected_child_items = [
            d for d in self.child_items if d.parent_item_code in combos_to_split
        ]

        to_remove: list[SalesOrderItem] = []
        for d in self.items:
            if d.item_code in combos_to_split:
                to_remove.append(d)

        for d in to_remove:
            self.items.remove(d)

        for d in selected_child_items:
            self.append(
                "items",
                {"item_code": d.item_code, "item_name": d.item_name, "qty": d.qty},
            )

        for d in combos_to_split:
            child: SalesOrderItem = frappe.get_doc(
                "Sales Order Item", {"parent": self.name, "item_code": d}
            )
            if child.docstatus == 1:
                child.cancel()
            child.delete()

        if save:
            self.save()


@frappe.whitelist()  # pragma: no cover
@frappe.validate_and_sanitize_search_inputs
def sales_order_item_query(
    doctype: str,
    txt: str,
    searchfield: str,
    start: int,
    page_len: int,
    filters: dict[Any, Any],
):
    from comfort.fixtures.hooks.queries import default_query

    field = "from_actual_stock"
    if filters.get(field) is not None:
        available_items: Generator[str, None, None] = (
            d.item_code
            for d in frappe.get_all("Bin", "item_code", {"available_actual": [">", 0]})
        )
        filters["item_code"] = ["in", available_items]
        del filters[field]
    return default_query(doctype, txt, searchfield, start, page_len, filters)
