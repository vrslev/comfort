from __future__ import annotations

# TODO: Allow change services on submit
from typing import Any, Generator, Iterable

import frappe
from comfort import ValidationError, count_quantity, group_by_key
from comfort.comfort_core.doctype.commission_settings.commission_settings import (
    CommissionSettings,
)
from comfort.entities.doctype.child_item.child_item import ChildItem
from comfort.entities.doctype.item.item import Item
from comfort.finance import get_account, get_paid_amount
from comfort.finance.doctype.gl_entry.gl_entry import GLEntry
from comfort.stock.doctype.bin.bin import Bin
from frappe import _
from frappe.model.document import Document

from ..purchase_order_sales_order.purchase_order_sales_order import (
    PurchaseOrderSalesOrder,
)
from ..sales_order_child_item.sales_order_child_item import SalesOrderChildItem
from ..sales_order_item.sales_order_item import SalesOrderItem
from ..sales_order_service.sales_order_service import SalesOrderService


class SalesOrderMethods(Document):
    items: list[SalesOrderItem]
    child_items: list[SalesOrderChildItem]
    services: list[SalesOrderService]
    items_cost: int
    commission: int
    total_amount: int
    total_quantity: int
    total_weight: float
    service_amount: int
    edit_commission: bool
    margin: int
    discount: int
    paid_amount: int
    per_paid: int
    pending_amount: int
    payment_status: str
    delivery_status: str
    status: str

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
        to_remove: Generator[SalesOrderItem] = (
            item for item in self.items if item.qty == 0
        )
        for item in to_remove:
            self.items.remove(item)

    def _update_items_from_db(self):
        """Load item properties from database and calculate Amount and Total Weight."""
        for item in self.items:
            doc: Item = frappe.get_cached_doc("Item", item.item_code)
            item.item_name = doc.item_name
            item.rate = doc.rate
            item.weight = doc.weight

            item.amount = item.rate * item.qty
            item.total_weight = item.weight * item.qty

    def _calculate_item_totals(self):
        """Calculate global Total Quantity, Weight and Items Cost."""
        self.total_quantity, self.total_weight, self.items_cost = 0, 0.0, 0
        for item in self.items:
            self.total_quantity += item.qty
            self.total_weight += item.total_weight
            self.items_cost += item.amount

    def _calculate_service_amount(self):  # TODO: Property
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
            self.margin = 0.0
            return

        base_margin = self.items_cost * self.commission / 100
        items_cost_rounding_remainder = round(self.items_cost, -1) - self.items_cost
        rounded_margin = round(base_margin, -1) + items_cost_rounding_remainder
        self.margin = rounded_margin

    def _calculate_total_amount(self):
        self.total_amount = (
            self.items_cost + self.margin + self.service_amount - self.discount
        )

    def _set_paid_and_pending_per_amount(self):
        # TODO: Property
        self.paid_amount = get_paid_amount(self.doctype, self.name)

        if int(self.total_amount) == 0:
            self.per_paid = 100
        else:
            self.per_paid = self.paid_amount / self.total_amount * 100

        self.pending_amount = self.total_amount - self.paid_amount

    def calculate(self):  # pragma: no cover
        """Calculate all things that are calculable."""
        self._update_items_from_db()
        self._calculate_item_totals()
        self._calculate_service_amount()
        self._calculate_commission()
        self._calculate_margin()
        self._calculate_total_amount()
        self._set_paid_and_pending_per_amount()

    def set_child_items(self):
        """Generate Child Items from combinations in Items."""

        self.child_items = []
        if not self.items:
            return

        child_items: list[ChildItem] = frappe.get_all(
            "Child Item",
            fields=("parent as parent_item_code", "item_code", "item_name", "qty"),
            filters={"parent": ("in", (d.item_code for d in self.items))},
        )

        item_codes_to_qty = count_quantity(self.items)
        for d in child_items:
            d.qty = d.qty * item_codes_to_qty[d.parent_item_code]

        self.extend("child_items", child_items)


class SalesOrderFinance(SalesOrderMethods):
    def _get_amounts_for_invoice_gl_entries(self):
        sales_amount = self.total_amount - self.service_amount

        delivery_amount, installation_amount = 0, 0
        for s in self.services:
            if "Delivery" in s.type:  # TODO: Test this with translation
                delivery_amount += s.rate
            elif "Installation" in s.type:
                installation_amount += s.rate

        return {
            "sales_amount": sales_amount,
            "delivery_amount": delivery_amount,
            "installation_amount": installation_amount,
        }

    def _make_categories_invoice_gl_entries(
        self,
        paid_amount: int,
        sales_amount: int,
        delivery_amount: int,
        installation_amount: int,
    ):
        remaining_amount = paid_amount

        for accounts_name, amount in (
            ("sales", sales_amount),
            ("delivery", delivery_amount),
            ("installation", installation_amount),
        ):
            if amount == 0:
                continue

            elif amount > remaining_amount:
                GLEntry.new(
                    self, "Invoice", get_account(accounts_name), 0, remaining_amount
                )
                remaining_amount = 0
                break

            else:
                GLEntry.new(self, "Invoice", get_account(accounts_name), 0, amount)
                remaining_amount -= amount

        if remaining_amount > 0:
            GLEntry.new(self, "Invoice", get_account("sales"), 0, remaining_amount)
            remaining_amount = 0

    def _make_income_invoice_gl_entry(self, paid_amount: int, paid_with_cash: bool):
        account = get_account("cash" if paid_with_cash else "bank")
        GLEntry.new(self, "Invoice", account, paid_amount, 0)

    def make_invoice_gl_entries(self, paid_amount: int, paid_with_cash: bool):
        """Automatically allocate Paid Amount to various funds and make GL Entries."""

        if paid_amount <= 0:
            raise ValidationError(_("Paid Amount should be more that zero"))
        elif self.total_amount <= 0:
            raise ValidationError(_("Total Amount should be more that zero"))

        amounts = self._get_amounts_for_invoice_gl_entries()
        self._make_categories_invoice_gl_entries(paid_amount, **amounts)
        self._make_income_invoice_gl_entry(paid_amount, paid_with_cash)

    def make_delivery_gl_entries(self):
        """Make GL Entries for event of delivery according to Accounting cycle.
        Executed when order is completed.
        """
        accounts = get_account(("inventory", "cost_of_goods_sold"))
        GLEntry.new(self, "Delivery", accounts[0], 0, self.items_cost)
        GLEntry.new(self, "Delivery", accounts[1], self.items_cost, 0)


class SalesOrderStock(SalesOrderFinance):
    def _get_items_with_splitted_combinations(
        self,
    ) -> list[SalesOrderChildItem | SalesOrderItem]:
        parents = (d.parent_item_code for d in self.child_items)
        return self.child_items + [d for d in self.items if d.item_code not in parents]

    def remove_all_items_from_bin(self):
        """Reduce Reserved Actual quantity in Bins of items in Sales Order.
        Executed when order is completed.
        """
        items = self._get_items_with_splitted_combinations()
        for item_code, qty in count_quantity(items).items():
            Bin.update_for(item_code, reserved_actual=-qty)


class SalesOrderStatuses(SalesOrderStock):
    def _set_payment_status(self):
        """Set Payment Status. Depends on `per_paid`.
        If docstatus == 2 sets "".
        """
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
        """Set Delivery Status. Depends on status of linked Purchase Order.
        If docstatus == 2 sets "".
        """
        status = "To Purchase"
        if self.delivery_status == "Delivered":
            return
        elif self.docstatus == 2:
            status = ""
        else:
            po_name: list[PurchaseOrderSalesOrder] = frappe.get_all(
                "Purchase Order Sales Order",
                fields="parent",
                filters={"sales_order_name": self.name, "docstatus": 1},
                limit_page_length=1,
            )
            if po_name:
                po_status: str = frappe.get_value(
                    "Purchase Order", po_name[0].parent, "status"
                )
                if po_status == "To Receive":
                    status = "Purchased"
                elif po_status == "Completed":
                    status = "To Deliver"

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
        self._set_delivery_status()
        self._set_payment_status()
        self._set_document_status()

    @frappe.whitelist()
    def set_paid(self, paid_amount: int, cash: bool):
        """Add new Payment."""
        self.make_invoice_gl_entries(paid_amount, cash)
        self._set_paid_and_pending_per_amount()
        self.set_statuses()
        self.db_update()

    @frappe.whitelist()
    def set_delivered(self):
        """Mark Sales Order as delivered"""
        self.set_statuses()  # TODO: Is this really sets delivery status?
        self.db_update()  # TODO: Is it appropriate?
        if self.delivery_status == "Delivered":
            self.make_delivery_gl_entries()
            self.remove_all_items_from_bin()
        else:
            raise ValidationError(_("Not able to set Delivered"))


class SalesOrder(SalesOrderStatuses):
    def validate(self):
        # SalesOrderMethods
        self.merge_same_items()
        self.delete_empty_items()
        self.calculate()
        self.set_child_items()

        # SalesOrderStatuses
        self.set_statuses()

    def before_submit(self):
        self.edit_commission = True
        # stock.sales_order_from_stock_submitted(self)

    def on_cancel(self):
        # TODO: Cancel payment and delivery
        # TODO: Update bin
        self.ignore_linked_doctypes = "GL Entry"  # type: ignore

        GLEntry.make_reverse_entries(self)

        self._set_paid_and_pending_per_amount()
        self.set_statuses()

    def before_update_after_submit(self):  # TODO
        if self.from_not_received_items_to_sell:  # type: ignore
            self.flags.ignore_validate_update_after_submit = True
        self.validate()

    @frappe.whitelist()
    def calculate_commission_and_margin(self):
        self._calculate_commission()
        self._calculate_margin()

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


@frappe.whitelist()
@frappe.validate_and_sanitize_search_inputs
def sales_order_item_query(
    doctype: str,
    txt: str,
    searchfield: str,
    start: str,
    page_len: str,
    filters: dict[Any, Any],
):
    from comfort.fixtures.hooks.queries import default_query

    field = "from_actual_stock"
    if filters.get(field) is not None:
        if filters[field]:
            available_items: list[str] = [
                d.item_code
                for d in frappe.get_all(
                    "Bin", "item_code", {"available_actual": [">", 0]}
                )
            ]
            filters["item_code"] = ["in", available_items]
        del filters[field]
    return default_query(doctype, txt, searchfield, start, page_len, filters)
