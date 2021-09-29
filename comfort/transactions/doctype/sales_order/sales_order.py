from __future__ import annotations

from typing import TYPE_CHECKING, Any, Iterable, Literal

import frappe
from comfort import ValidationError, count_qty, group_by_attr
from comfort.comfort_core.doctype.commission_settings.commission_settings import (
    CommissionSettings,
)
from comfort.comfort_core.hooks import default_query
from comfort.entities.doctype.child_item.child_item import ChildItem
from comfort.entities.doctype.item.item import Item
from comfort.finance import create_payment, get_account
from comfort.stock import create_receipt, create_stock_entry, get_stock_balance
from comfort.transactions import delete_empty_items, merge_same_items
from frappe import _
from frappe.model.document import Document

from ..purchase_order_sales_order.purchase_order_sales_order import (
    PurchaseOrderSalesOrder,
)
from ..sales_order_child_item.sales_order_child_item import SalesOrderChildItem
from ..sales_order_item.sales_order_item import SalesOrderItem
from ..sales_order_service.sales_order_service import SalesOrderService

if TYPE_CHECKING:
    from comfort.finance.doctype.payment.payment import Payment
    from comfort.stock.doctype.receipt.receipt import Receipt

    from ..purchase_order.purchase_order import PurchaseOrder
    from ..purchase_order_item_to_sell.purchase_order_item_to_sell import (
        PurchaseOrderItemToSell,
    )
    from ..sales_return.sales_return import SalesReturn


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
    from_available_stock: Literal[
        "Available Purchased", "Available Actual"
    ] | None = None
    from_purchase_order: str | None = None

    ignore_linked_doctypes: list[str]

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

    def _validate_from_available_stock(self):
        if not self.from_available_stock:
            return
        validate_from_available_stock_params(
            self.from_available_stock, self.from_purchase_order
        )
        order_counter = count_qty(self._get_items_with_splitted_combinations())

        if self.from_available_stock == "Available Actual":
            stock_counter = get_stock_balance(self.from_available_stock)
        else:
            items_to_sell: list[PurchaseOrderItemToSell] = frappe.get_all(
                "Purchase Order Item To Sell",
                fields=("item_code", "qty"),
                filters={"parent": ("in", self.from_purchase_order)},
            )
            stock_counter = count_qty(items_to_sell)

        for item_code, qty in order_counter.items():
            if stock_counter[item_code] < qty:
                raise ValidationError(
                    _("Insufficient stock for Item {}").format(item_code)
                )

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

    def _create_cancel_sales_return(self):
        sales_return: SalesReturn = frappe.new_doc("Sales Return")
        sales_return.sales_order = self.name
        sales_return.__voucher = self._doc_before_save
        sales_return.add_items(sales_return.get_items_available_to_add())
        sales_return.flags.sales_order_on_cancel = True
        sales_return.flags.ignore_links = True
        sales_return.save()
        sales_return.submit()

    def _modify_purchase_order_for_from_available_stock(self):
        if self.from_available_stock != "Available Purchased":
            return

        doc: PurchaseOrder = frappe.get_doc("Purchase Order", self.from_purchase_order)

        # Remove items to sell
        qty_counter = count_qty(self.items)
        for item in doc.items_to_sell:
            if item.item_code in qty_counter:
                item.qty -= qty_counter[item.item_code]
                del qty_counter[item.item_code]

        # Add Purchase Order Sales Order
        doc.append(
            "sales_orders",
            {
                "sales_order_name": self.name,
                "customer": self.customer,
                "total_amount": self.total_amount,
            },
        )

        delete_empty_items(doc, "items_to_sell")
        doc.calculate()
        doc.db_update()
        doc.update_children()

    def _make_stock_entries_for_from_available_stock(self):
        """
        If from Available Purchased:
            via Checkout
            Available Purchased -> Reserved Purchased
        If from Available Actual:
            via Receipt
            Available Actual -> Reserved Actual

        After making this stock entries Sales Order becomes regular Sales Order i. e. everything else is as usual
        Are GL Entries required? No!

        # TODO: Set statuses
            solution: by modifying Purchase Order
        # TODO: Modify Purchase Order
        On cancel:
            On cancel Sales Return is being created which handles items transfer from Reserved to Available

        # TODO: Is adding items from multiple Purchase orders allowed in case of actual stock?


        If we don't change Purchase Order's items to sell, Purchase Return might work!
        But then it is not that comfy


        If Sales Order is from Available Actual stock then it goes out of Purchase Order print format which I was worried about.

        So,
        If Available Purchased:
            modify Purchase Order (items to sell -> purchase order sales order)
            make Stock Entries

        If Available Actual:
            make Stock Entries # TODO: Which entries to make? How to reverse it on cancel? How change statuses?

        Possibly better way to make sales order from actual stock is to change stock type in Sales Receipt

        """
        if not self.from_available_stock:
            return

        stock_types = {
            "Available Purchased": ("Available Purchased", "Reserved Purchased"),
            "Available Actual": ("Available Actual", "Reserved Actual"),
        }[self.from_available_stock]
        ref_doctype = {
            "Available Purchased": "Checkout",
            "Available Actual": "Sales Order",
        }[self.from_available_stock]

        if self.from_available_stock == "Available Purchased":
            ref_name = frappe.get_value(
                ref_doctype, {"purchase_order": self.from_purchase_order}
            )
        else:
            ref_name = self.name

        items = self._get_items_with_splitted_combinations()
        create_stock_entry(
            ref_doctype, ref_name, stock_types[0], items, reverse_qty=True
        )
        create_stock_entry(ref_doctype, ref_name, stock_types[1], items)


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
        elif self.from_available_stock == "Available Actual":
            if self.docstatus == 0:
                status = "To Purchase"
            else:
                status = "To Deliver"
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
        self._validate_from_available_stock()

        self.calculate()
        self.set_statuses()

    def before_submit(self):
        self.edit_commission = True
        self._modify_purchase_order_for_from_available_stock()
        self._make_stock_entries_for_from_available_stock()

    def before_cancel(self):  # pragma: no cover
        self.set_statuses()
        self._create_cancel_sales_return()

    def on_cancel(self):  # TODO: Cover
        self.ignore_linked_doctypes = [
            "Purchase Order",
            "Sales Return",
            "Payment",
            # Stock Entry shouldn't be cancelled because
            # we create Stock Entry in on-cancel Sales Return
            "Stock Entry",
        ]

        # TODO: Make (of find) generic `cancel_for` function
        payments: list[Payment] = frappe.get_all(
            "Payment", {"voucher_type": self.doctype, "voucher_no": self.name}
        )
        for payment in payments:
            payment: Payment = frappe.get_doc("Payment", payment.name)
            payment.cancel()
        receipts: list[Receipt] = frappe.get_all(
            "Receipt", {"voucher_type": self.doctype, "voucher_no": self.name}
        )
        for receipt in receipts:
            receipt: Payment = frappe.get_doc("Receipt", receipt.name)
            receipt.cancel()

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


@frappe.whitelist()
def get_sales_orders_not_in_purchase_order() -> list[str]:
    # TODO: Validate status so completed orders from actual stock are good
    po_sales_orders: list[PurchaseOrderSalesOrder] = frappe.get_all(
        "Purchase Order Sales Order", "sales_order_name"
    )
    return [
        s.name
        for s in frappe.get_all(
            "Sales Order",
            {"name": ("not in", (s.sales_order_name for s in po_sales_orders))},
        )
    ]


@frappe.whitelist()
def validate_from_available_stock_params(
    from_available_stock: Literal["Available Purchased", "Available Actual"] | None,
    from_purchase_order: str | None = None,
):
    if from_available_stock == "Available Purchased":
        if not from_purchase_order:
            raise ValidationError(
                _(
                    "If From Available Stock is Available Purchased, From Purchase Order should be set"
                )
            )
        status: str = frappe.get_value("Purchase Order", from_purchase_order, "status")
        if status != "To Receive":
            raise ValidationError(_("Status of Purchase Order should be To Receive"))

        items_to_sell: list[PurchaseOrderItemToSell] = frappe.get_all(
            "Purchase Order Item To Sell",
            fields="item_code",
            filters={"parent": ("in", from_purchase_order)},
        )
        if not items_to_sell:
            raise ValidationError(_("No Items To Sell in Purchase Order"))
    elif from_available_stock == "Available Actual":
        if not get_stock_balance(from_available_stock):
            raise ValidationError(_("No Items in Available Actual stock"))


@frappe.whitelist()
def item_query(
    doctype: str,
    txt: str,
    searchfield: str,
    start: int,
    page_len: int,
    filters: dict[str, Any],
):
    from_available_stock: Literal[
        "Available Purchased", "Available Actual"
    ] | None = filters.get("from_available_stock")
    from_purchase_order: str | None = filters.get("from_purchase_order")

    validate_from_available_stock_params(from_available_stock, from_purchase_order)

    acceptable_item_codes: Iterable[str] | None = None

    if from_available_stock == "Available Actual":
        acceptable_item_codes = get_stock_balance(from_available_stock).keys()
    elif from_available_stock == "Available Purchased":
        items_to_sell: list[PurchaseOrderItemToSell] = frappe.get_all(
            "Purchase Order Item To Sell",
            fields="item_code",
            filters={"parent": ("in", from_purchase_order)},
        )
        acceptable_item_codes = (d.item_code for d in items_to_sell)

    if acceptable_item_codes is None:
        filters = {}
    else:
        filters = {"item_code": ("in", acceptable_item_codes)}

    return default_query(
        doctype=doctype,
        txt=txt,
        searchfield=searchfield,
        start=start,
        page_len=page_len,
        filters=filters,
    )
