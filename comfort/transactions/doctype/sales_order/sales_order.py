from __future__ import annotations

from typing import Iterable, Literal

import frappe
from comfort import ValidationError, count_qty, group_by_attr
from comfort.comfort_core.doctype.commission_settings.commission_settings import (
    CommissionSettings,
)
from comfort.entities.doctype.child_item.child_item import ChildItem
from comfort.entities.doctype.item.item import Item
from comfort.finance import create_payment, get_account
from comfort.stock import create_receipt
from comfort.transactions import delete_empty_items, merge_same_items
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
    delivery_status: Literal["", "To Purchase", "Purchased", "To Deliver", "Delivered"]

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

        child_items: list[SalesOrderChildItem] = frappe.get_all(
            "Child Item",
            fields=("parent as parent_item_code", "item_code", "item_name", "qty"),
            filters={"parent": ("in", (d.item_code for d in self.items))},
        )

        item_codes_to_qty = count_qty(self.items)
        for item in child_items:
            item.qty = item.qty * item_codes_to_qty[item.parent_item_code]

        self.extend("child_items", child_items)

    def _calculate_item_totals(self):
        """Calculate global Total Quantity, Weight and Items Cost."""
        self.total_quantity, self.total_weight, self.items_cost = 0, 0.0, 0
        for item in self.items:
            item.total_weight = item.qty * item.weight
            item.amount = item.qty * item.rate

            self.total_quantity += item.qty
            self.total_weight += item.total_weight
            self.items_cost += item.amount

    def _calculate_service_amount(self):
        self.service_amount = sum(s.rate for s in self.services)

    def _calculate_commission(self):
        """Calculate commission based rules set in Commission Settings if `edit_commission` is False."""
        # TODO: Issues when Commission Settings have no ranges and when Edit commission
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

    def _get_items_with_splitted_combinations(
        self,
    ) -> list[SalesOrderChildItem | SalesOrderItem]:
        parents = [child.parent_item_code for child in self.child_items]
        return self.child_items + [
            item for item in self.items if item.item_code not in parents
        ]


class SalesOrderStatuses(SalesOrderMethods):
    def _get_paid_amount(self):
        payments: list[str] = [
            p.name
            for p in frappe.get_all(
                "Payment", {"voucher_type": self.doctype, "voucher_no": self.name}
            )
        ]
        returns: list[str] = [
            r.name for r in frappe.get_all("Sales Return", {"sales_order": self.name})
        ]

        balances: list[tuple[int]] = frappe.get_all(
            "GL Entry",
            fields="SUM(debit - credit) as balance",
            filters={
                "account": ("in", (get_account("cash"), get_account("bank"))),
                "voucher_type": ("in", ("Payment", "Sales Return")),
                "voucher_no": ("in", payments + returns),
                "docstatus": ("!=", 2),
            },
            as_list=True,
        )
        return sum(b[0] or 0 for b in balances)

    def _set_paid_and_pending_per_amount(self):
        self.paid_amount = self._get_paid_amount()

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

        self.payment_status = status

    def _set_delivery_status(self):
        if self.docstatus == 2:
            status = ""
        elif frappe.db.exists(
            "Receipt",
            {"voucher_type": self.doctype, "voucher_no": self.name, "docstatus": 1},
        ):
            status = "Delivered"
        else:
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

        self.delivery_status = status

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

        self.status = status

    def set_statuses(self):  # pragma: no cover
        """Set statuses according to current Sales Order and linked Purchase Order states."""
        self._set_paid_and_pending_per_amount()
        self._set_payment_status()
        self._set_delivery_status()
        self._set_document_status()


class SalesOrder(SalesOrderStatuses):
    def validate(self):  # pragma: no cover
        delete_empty_items(self, "items")
        self.items = merge_same_items(self.items)
        self.update_items_from_db()
        self.set_child_items()

        self.calculate()
        self.set_statuses()

    def before_submit(self):
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
    def add_payment(self, paid_amount: int, cash: bool):
        if self.docstatus == 2:
            raise ValidationError(
                _("Sales Order should be not cancelled to add Payment")
            )
        create_payment(self.doctype, self.name, paid_amount, cash)  # pragma: no cover
        self.set_statuses()  # pragma: no cover
        self.db_update()  # pragma: no cover

    @frappe.whitelist()
    def add_receipt(self):
        if self.docstatus == 2:
            raise ValidationError(
                _("Sales Order should be not cancelled to add Receipt")
            )
        if self.delivery_status != "To Deliver":
            raise ValidationError(
                _('Delivery Status Sales Order should be "To Deliver" to add Receipt')
            )

        create_receipt(self.doctype, self.name)  # pragma: no cover
        self.set_statuses()  # pragma: no cover
        self.db_update()  # pragma: no cover

    @frappe.whitelist()
    def split_combinations(self, combos_docnames: Iterable[str], save: bool):
        # TODO: Check if there's any child items with this item_codes before removing them. Otherwise throw ValidationError
        combos_docnames = list(set(combos_docnames))

        items_to_remove: list[SalesOrderItem] = []
        removed_combos: list[dict[str, str | int]] = []
        for item in self.items:
            if item.name in combos_docnames:
                items_to_remove.append(item)
                removed_combos.append(
                    frappe._dict(item_code=item.item_code, qty=item.qty)
                )

        for item in items_to_remove:
            self.items.remove(item)

        parent_item_codes_to_qty = count_qty(removed_combos)

        child_items: list[ChildItem] = frappe.get_all(
            "Child Item",
            fields=("parent", "item_code", "qty"),
            filters={"parent": ("in", parent_item_codes_to_qty.keys())},
        )

        for parent_item_code, items in group_by_attr(child_items, "parent").items():
            parent_item_code: str
            items: list[ChildItem]
            parent_qty = parent_item_codes_to_qty[parent_item_code]
            for item in items:
                self.append(
                    "items", {"item_code": item.item_code, "qty": item.qty * parent_qty}
                )

        if save:
            self.save()


@frappe.whitelist()
def has_linked_delivery_trip(sales_order_name: str):
    return (
        True
        if frappe.db.exists(
            {"doctype": "Delivery Stop", "sales_order": sales_order_name}
        )
        else False
    )
