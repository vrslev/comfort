from __future__ import annotations

import json
import re
from collections import Counter
from datetime import datetime, timedelta
from types import SimpleNamespace
from typing import Any, Literal, TypedDict

from ikea_api.wrappers.types import DeliveryService

import frappe
from comfort.comfort_core import CommissionSettings
from comfort.entities import ChildItem, Item
from comfort.finance import Payment
from comfort.finance.utils import create_payment, get_account
from comfort.integrations.ikea import fetch_items, get_delivery_services
from comfort.stock import Receipt
from comfort.stock.utils import create_receipt, create_stock_entry, get_stock_balance
from comfort.transactions.doctype.purchase_order_item_to_sell.purchase_order_item_to_sell import (
    PurchaseOrderItemToSell,
)
from comfort.transactions.doctype.purchase_order_sales_order.purchase_order_sales_order import (
    PurchaseOrderSalesOrder,
)
from comfort.transactions.doctype.sales_order_child_item.sales_order_child_item import (
    SalesOrderChildItem,
)
from comfort.transactions.doctype.sales_order_item.sales_order_item import (
    SalesOrderItem,
)
from comfort.transactions.doctype.sales_order_service.sales_order_service import (
    SalesOrderService,
)
from comfort.transactions.utils import delete_empty_items, merge_same_items
from comfort.utils import (
    TypedDocument,
    ValidationError,
    _,
    count_qty,
    counters_are_same,
    doc_exists,
    get_all,
    get_cached_doc,
    get_doc,
    get_value,
    group_by_attr,
    new_doc,
)
from frappe.utils.print_format import get_pdf


class _SplitOrderItem(TypedDict):
    item_code: str
    qty: int


class _CheckAvailabilityDeliveryOptionItem(TypedDict):
    item_code: str
    item_name: str | None
    available_qty: int
    required_qty: int


class _CheckAvailabilityDeliveryOption(TypedDict):
    delivery_type: str
    items: list[_CheckAvailabilityDeliveryOptionItem]


class _CheckAvailabilityCannotAddItem(TypedDict):
    item_code: str
    item_name: str | None


class _CheckAvailabilityResponse(TypedDict):
    options: list[_CheckAvailabilityDeliveryOption]
    cannot_add: list[_CheckAvailabilityCannotAddItem]


class SalesOrder(TypedDocument):
    doctype: Literal["Sales Order"]

    customer: str
    # TODO: List is mutating thing. It is unsafe to set all of this in class definition.
    items: list[SalesOrderItem] = []
    services: list[SalesOrderService] = []
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
    child_items: list[SalesOrderChildItem] = []
    status: Literal["Draft", "In Progress", "Completed", "Cancelled"]
    payment_status: Literal["", "Unpaid", "Partially Paid", "Paid", "Overpaid"]
    per_paid: float
    delivery_status: Literal["", "To Purchase", "Purchased", "To Deliver", "Delivered"]
    from_available_stock: Literal[
        "Available Purchased", "Available Actual"
    ] | None = None
    from_purchase_order: str | None = None

    ignore_linked_doctypes: list[str]
    _doc_before_save: SalesOrder

    #########
    # Hooks #
    #########

    def validate(self) -> None:
        self._validate_from_available_stock()

        delete_empty_items(self, "items")
        self.items = merge_same_items(self.items)
        self.update_items_from_db()
        self.set_child_items()

        self.calculate()
        self.set_statuses()

    def before_submit(self) -> None:  # pragma: no cover
        self.edit_commission = True
        if self.from_available_stock:
            self._modify_purchase_order_for_from_available_stock()
            self._make_stock_entries_for_from_available_stock()
            self.set_statuses()
            self.from_purchase_order = None

    def before_cancel(self) -> None:  # pragma: no cover
        self.set_statuses()
        self._create_cancel_sales_return()

    def on_cancel(self) -> None:

        self.ignore_linked_doctypes = [
            "Purchase Order",
            "Sales Return",
            "Payment",
            # Stock Entry shouldn't be cancelled because
            # we create Stock Entry in on-cancel Sales Return
            "Stock Entry",
        ]

        payload = {"voucher_type": self.doctype, "voucher_no": self.name}

        for doctype in Payment, Receipt:
            for doc in get_all(doctype, filter=payload, field=("name", "docstatus")):
                if doc.docstatus != 2:
                    get_doc(doctype, doc.name).cancel()

    def before_update_after_submit(self) -> None:  # pragma: no cover
        self._validate_services_not_changed()
        self.calculate()
        self.set_statuses()

    ################
    # End of hooks #
    ################

    def update_items_from_db(self) -> None:
        """Load item properties from cache or database and calculate Amount and Total Weight."""

        for item in self.items:
            doc = get_cached_doc(Item, item.item_code)
            item.item_name = doc.item_name
            if not (self.from_available_stock and item.rate):
                item.rate = doc.rate
            item.weight = doc.weight

            item.amount = item.rate * item.qty
            item.total_weight = item.weight * item.qty

    def set_child_items(self) -> None:
        """Generate Child Items from combinations in Items."""

        self.child_items = []
        if not self.items:
            return

        child_items = get_all(
            ChildItem,
            field=("parent as parent_item_code", "item_code", "item_name", "qty"),
            filter={"parent": ("in", (i.item_code for i in self.items))},
        )

        item_codes_to_qty = count_qty(self.items)
        for item in child_items:
            item.qty = item.qty * item_codes_to_qty[item.parent_item_code]  # type: ignore

        self.extend("child_items", child_items)

    def _validate_from_available_stock(self):
        if not self.from_available_stock:
            return

        validate_params_from_available_stock(
            self.from_available_stock, self.from_purchase_order
        )

        self.set_child_items()
        order_counter = count_qty(self.get_items_with_splitted_combinations())

        if self.from_available_stock == "Available Actual":
            stock_counter = get_stock_balance(self.from_available_stock)
        else:
            from comfort.transactions import PurchaseOrder

            doc = get_doc(PurchaseOrder, self.from_purchase_order)
            items_to_sell = doc.get_items_to_sell(split_combinations=True)
            stock_counter = count_qty(items_to_sell)

        for item_code, qty in order_counter.items():
            if stock_counter[item_code] < qty:
                raise ValidationError(
                    _(
                        "Insufficient stock for Item {}. Required: {}, available: {}"
                    ).format(item_code, qty, stock_counter[item_code])
                )

    def _calculate_item_totals(self) -> None:
        """Calculate global Total Quantity, Weight and Items Cost."""
        self.total_quantity, self.total_weight, self.items_cost = 0, 0.0, 0
        for item in self.items:
            item.total_weight = item.qty * item.weight
            item.amount = item.qty * item.rate

            self.total_quantity += item.qty
            self.total_weight += item.total_weight
            self.items_cost += item.amount

    def _calculate_service_amount(self) -> None:
        self.service_amount = sum(s.rate for s in self.services)

    def _calculate_commission(self) -> None:
        """Calculate commission based rules set in Commission Settings if `edit_commission` is False."""
        if self.items_cost and not self.edit_commission:
            self.commission = CommissionSettings.get_commission_percentage(
                self.items_cost
            )

    def _calculate_margin(self) -> None:
        """Calculate margin based on commission and rounding remainder of items_cost."""
        if self.items_cost <= 0:
            self.margin = 0
            return
        base_margin = self.items_cost * self.commission / 100
        items_cost_rounding_remainder = round(self.items_cost, -1) - self.items_cost
        rounded_margin = int(round(base_margin, -1) + items_cost_rounding_remainder)
        self.margin = rounded_margin

    def _calculate_total_amount(self) -> None:
        self.total_amount = (
            self.items_cost + self.margin + self.service_amount - self.discount
        )

    def calculate(self) -> None:
        """Calculate all things that are calculable."""
        self._calculate_item_totals()
        self._calculate_service_amount()
        self._calculate_commission()
        self._calculate_margin()
        self._calculate_total_amount()

    def _validate_services_not_changed(self):
        if self.delivery_status in (
            "To Purchase",
            "Purchased",
            "To Deliver",
        ):
            return

        def services_changed() -> bool | None:
            self.load_doc_before_save()

            if len(self.services) != len(self._doc_before_save.services):
                return True

            for idx, service in enumerate(self.services):
                service_before_save = self._doc_before_save.services[idx]

                if (
                    service.type != service_before_save.type
                    or service.rate != service_before_save.rate
                ):
                    return True

        if services_changed():
            raise ValidationError(
                _(
                    "Allowed to change services in Sales Order only if delivery"
                    + " status is To Purchase, Purchased or To Deliver"
                )
            )

    def get_items_with_splitted_combinations(
        self,
    ) -> list[SalesOrderChildItem | SalesOrderItem]:
        parents = [child.parent_item_code for child in self.child_items]
        return self.child_items + [  # type: ignore
            item for item in self.items if item.item_code not in parents
        ]

    def _create_cancel_sales_return(self) -> None:
        if self.flags.on_cancel_from_sales_return:
            return

        from comfort.transactions import SalesReturn

        sales_return = new_doc(SalesReturn)
        sales_return.sales_order = self.name
        sales_return.__voucher = self._doc_before_save
        sales_return.add_items(sales_return.get_items_available_to_add())
        sales_return.flags.sales_order_on_cancel = True
        sales_return.flags.ignore_links = True
        sales_return.save()
        sales_return.submit()

    def _modify_purchase_order_for_from_available_stock(self) -> None:
        if self.from_available_stock != "Available Purchased":
            return

        from comfort.transactions import PurchaseOrder

        doc = get_doc(PurchaseOrder, self.from_purchase_order)

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
                "docstatus": 1,
            },
        )

        delete_empty_items(doc, "items_to_sell")
        doc.calculate()
        doc.save_without_validating()

    def _make_stock_entries_for_from_available_stock(self) -> None:
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

        ref_name: str = (
            get_value(ref_doctype, {"purchase_order": self.from_purchase_order})
            if self.from_available_stock == "Available Purchased"
            else self.name
        )
        items = self.get_items_with_splitted_combinations()

        create_stock_entry(
            ref_doctype, ref_name, stock_types[0], items, reverse_qty=True  # type: ignore
        )
        create_stock_entry(ref_doctype, ref_name, stock_types[1], items)  # type: ignore

    def _get_paid_amount(self):
        payments = get_all(
            Payment,
            pluck="name",
            filter={"voucher_type": self.doctype, "voucher_no": self.name},
        )
        returns: list[Any] = frappe.get_all(
            "Sales Return", filters={"sales_order": self.name}, pluck="name"
        )
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

    def set_paid_and_pending_per_amount(self) -> None:
        self.paid_amount = self._get_paid_amount()

        if self.total_amount == 0:
            self.per_paid = 100
        else:
            self.per_paid = self.paid_amount / self.total_amount * 100

        self.pending_amount = self.total_amount - self.paid_amount

    def _set_payment_status(self) -> None:
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

    def _set_delivery_status(self) -> None:
        if self.docstatus == 2:
            status = ""
        elif doc_exists(
            "Receipt",
            {"voucher_type": self.doctype, "voucher_no": self.name, "docstatus": 1},
        ):
            status = "Delivered"
        elif self.from_available_stock == "Available Actual":
            if self.docstatus == 0:
                status = "To Purchase"
            else:
                status = "To Deliver"
        else:
            if purchase_order_name := get_value(
                "Purchase Order Sales Order",
                fieldname="parent",
                filters={"sales_order_name": self.name, "docstatus": 1},
            ):
                if doc_exists(
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

    def _set_document_status(self) -> None:
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

    def set_statuses(self) -> None:
        """Set statuses according to current Sales Order and linked Purchase Order states."""
        self.set_paid_and_pending_per_amount()
        self._set_payment_status()
        self._set_delivery_status()
        self._set_document_status()

    @frappe.whitelist()
    def add_payment(self, paid_amount: int, cash: bool):
        if self.docstatus == 2:
            raise ValidationError(
                _("Sales Order should be not Сancelled to add Payment")
            )
        create_payment(self.doctype, self.name, paid_amount, cash)
        self.set_statuses()
        self.save_without_validating()

    @frappe.whitelist()
    def add_receipt(self):
        if self.delivery_status != "To Deliver":
            raise ValidationError(
                _("Delivery Status Sales Order should be To Deliver to add Receipt")
            )

        create_receipt(self.doctype, self.name)
        self.set_statuses()
        self.save_without_validating()

    @frappe.whitelist()
    def split_combinations(self, combos_docnames: list[str], save: bool) -> None:
        combos_docnames = list(set(combos_docnames))

        items_to_remove: list[SalesOrderItem] = []
        removed_combos: list[SimpleNamespace] = []
        for item in self.items:
            if item.name in combos_docnames:
                items_to_remove.append(item)
                removed_combos.append(
                    SimpleNamespace(item_code=item.item_code, qty=item.qty)
                )

        for item in items_to_remove:
            self.items.remove(item)

        parent_item_codes_to_qty = count_qty(removed_combos)

        child_items = get_all(
            ChildItem,
            field=("parent", "item_code", "qty"),
            filter={"parent": ("in", parent_item_codes_to_qty.keys())},
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

    def _get_customer_first_name(self):
        matches = re.findall(r"\w+", self.customer)
        return matches[0] if matches else self.customer

    def _get_check_order_message_context(self):
        return {
            "customer_first_name": self._get_customer_first_name(),
            "items": self.items,
            "services": self.services,
            "total_amount": self.total_amount,
        }

    @frappe.whitelist()
    def generate_check_order_message(self) -> str:
        return frappe.render_template(  # type: ignore
            template="transactions/doctype/sales_order/check_order_message.j2",
            is_path=True,
            context=self._get_check_order_message_context(),
        )

    def _get_pickup_order_message_context(self):
        MONTHS = {
            1: "января",
            2: "февраля",
            3: "марта",
            4: "апреля",
            5: "мая",
            6: "июня",
            7: "июля",
            8: "августа",
            9: "сентября",
            10: "октября",
            11: "ноября",
            12: "декабря",
        }
        WEEKDAYS = {
            0: "в понедельник",
            1: "во вторник",
            2: "в среду",
            3: "в четверг",
            4: "в пятницу",
            5: "в субботу",
            6: "в воскресенье",
        }
        tomorrow = datetime.now() + timedelta(days=1)
        return {
            "customer_first_name": self._get_customer_first_name(),
            "weekday": WEEKDAYS[tomorrow.weekday()],
            "day": tomorrow.day,
            "month": MONTHS[tomorrow.month],
            "has_delivery": any("Delivery" in s.type for s in self.services),
            "pending_amount": self.pending_amount,
        }

    @frappe.whitelist()
    def generate_pickup_order_message(self) -> str:
        return frappe.render_template(  # type: ignore
            template="transactions/doctype/sales_order/pickup_order_message.j2",
            is_path=True,
            context=self._get_pickup_order_message_context(),
        )

    def _get_services_for_check_availability(self, qty_counter: Counter[str]):
        delivery_services = get_delivery_services(qty_counter)

        if delivery_services is None:
            return

        if delivery_services.cannot_add:
            return delivery_services

        if any(o.unavailable_items for o in delivery_services.delivery_options):
            return delivery_services

        frappe.msgprint(
            _("All items available"),
            alert=True,
            indicator="green",
        )

    @frappe.whitelist()
    def check_availability(self):
        items_with_splitted_combos = self.get_items_with_splitted_combinations()
        qty_counter = count_qty(items_with_splitted_combos)
        grouped_items: dict[
            str, list[SalesOrderItem | SalesOrderChildItem]
        ] = group_by_attr(items_with_splitted_combos)

        delivery_services = self._get_services_for_check_availability(qty_counter)
        if delivery_services is None:
            return

        def _get_delivery_type(option: DeliveryService):
            if option.service_provider and option.type:
                return f"{option.type} ({option.service_provider})"
            return option.type

        def _get_items(option: DeliveryService):
            return [
                _CheckAvailabilityDeliveryOptionItem(
                    item_code=item.item_code,
                    item_name=grouped_items[item.item_code][0].item_name,
                    available_qty=item.available_qty,
                    required_qty=qty_counter[item.item_code],
                )
                for item in option.unavailable_items
            ]

        options = [
            _CheckAvailabilityDeliveryOption(
                delivery_type=_get_delivery_type(option), items=_get_items(option)
            )
            for option in delivery_services.delivery_options
            if option.unavailable_items
        ]

        cannot_add = [
            _CheckAvailabilityCannotAddItem(
                item_code=item_code, item_name=grouped_items[item_code][0].item_name
            )
            for item_code in delivery_services.cannot_add
        ]
        return _CheckAvailabilityResponse(options=options, cannot_add=cannot_add)

    @frappe.whitelist()
    def fetch_items_specs(self):
        if self.from_available_stock:
            raise ValidationError(
                _("Can't fetch items specs if order is from Available Stock")
            )
        if self.status != "Draft":
            raise ValidationError(_("Can fetch items specs only if status is Draft"))

        response = fetch_items([i.item_code for i in self.items], force_update=True)
        if response["unsuccessful"]:
            frappe.msgprint(
                _("Cannot fetch those items: {}").format(
                    ", ".join(response["unsuccessful"])
                )
            )
        self.save()

    def _validate_split_order(self, qty_counter: Counter[str]):
        cur_counter = count_qty(self.items)

        if counters_are_same(cur_counter, qty_counter):
            raise ValidationError(
                _("Can't split Sales Order and include all the items")
            )

        for item_code, qty in qty_counter.items():
            if item_code not in cur_counter:
                raise ValidationError(_("No Item {} in Sales Order").format(item_code))
            if cur_counter[item_code] < qty:
                raise ValidationError(
                    _(
                        "Insufficient quantity for Item {}. Available: {}, you have: {}"
                    ).format(item_code, cur_counter[item_code], qty)
                )

    @frappe.whitelist()
    def split_order(self, items: list[_SplitOrderItem]):
        objectified_items = [SimpleNamespace(**i) for i in items]
        new_counter = count_qty(objectified_items)

        self._validate_split_order(new_counter)

        for item in self.items:
            item.qty -= new_counter[item.item_code]
            del new_counter[item.item_code]

        doc = new_doc(SalesOrder)
        doc.extend(
            "items",
            [
                {"item_code": item_code, "qty": qty}
                # Creating new counter because old one is modified
                for item_code, qty in count_qty(objectified_items).items()
            ],
        )
        doc.customer = self.customer
        doc.commission = self.commission
        self.edit_commission = doc.edit_commission = True
        doc.validate()

        self.save()
        doc.save()
        return doc.name


@frappe.whitelist()
def has_linked_delivery_trip(sales_order_name: str):
    name: Any = doc_exists(
        {
            "doctype": "Delivery Stop",
            "sales_order": sales_order_name,
            "docstatus": ("!=", 2),
        }
    )
    return bool(name)


@frappe.whitelist()
def get_sales_orders_not_in_purchase_order() -> list[str]:
    po_sales_orders = get_all(
        PurchaseOrderSalesOrder,
        field="sales_order_name",
        filter={"docstatus": ("!=", 2)},
    )
    filters = {
        "name": ("not in", (s.sales_order_name for s in po_sales_orders)),
        "docstatus": ("!=", 2),
        # Frappe makes Select fields with no value "" instead of None
        "from_available_stock": "",
    }
    return get_all(SalesOrder, pluck="name", filter=filters)


@frappe.whitelist()
@frappe.validate_and_sanitize_search_inputs
def purchase_order_filter_query(
    doctype: str,
    txt: str,
    searchfield: str,
    start: int,
    page_len: int,
    filters: dict[Any, Any],
):  # pragma: no cover
    from comfort.queries import default_query

    return default_query(
        doctype=doctype,
        txt=txt,
        searchfield=searchfield,
        start=start,
        page_len=page_len,
        filters=filters,
        order_by="creation DESC",
    )


@frappe.whitelist()
def get_sales_orders_in_purchase_order(purchase_order_name: str):
    po_sales_orders = get_all(
        PurchaseOrderSalesOrder,
        field="sales_order_name",
        filter={"parent": ("in", purchase_order_name)},
    )
    return [s.sales_order_name for s in po_sales_orders]


@frappe.whitelist()
def validate_params_from_available_stock(
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
        status: str = get_value("Purchase Order", from_purchase_order, "status")
        if status != "To Receive":
            raise ValidationError(_("Status of Purchase Order should be To Receive"))

        items_to_sell = get_all(
            PurchaseOrderItemToSell,
            field="item_code",
            filter={"parent": ("in", from_purchase_order)},
        )
        if not items_to_sell:
            raise ValidationError(_("Selected Purchase Order has no Items To Sell"))
    elif from_available_stock == "Available Actual":
        if not get_stock_balance(from_available_stock):
            raise ValidationError(_("No Items in Available Actual stock"))


@frappe.whitelist()
def calculate_commission_and_margin(doc: str):
    sales_order = SalesOrder(json.loads(doc))
    if sales_order.items_cost:
        sales_order._calculate_commission()
        sales_order._calculate_margin()
    return {"commission": sales_order.commission, "margin": sales_order.margin}


@frappe.whitelist()
def get_contract_template() -> None:  # pragma: no cover
    doc = new_doc(SalesOrder)
    doc.customer = "________________"
    doc.items = []
    html = frappe.get_print(doc=doc)  # type: ignore
    frappe.local.response.filename = "contract.pdf"
    frappe.local.response.filecontent = get_pdf(html)
    frappe.local.response.type = "pdf"
