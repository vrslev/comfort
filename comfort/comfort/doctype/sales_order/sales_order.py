# TODO: Allow change services on submit
from ... import stock
from comfort.comfort.ledger import (
    get_account,
    get_paid_amount,
    make_gl_entries,
    make_gl_entry,
    make_reverse_gl_entry,
)
import frappe
from frappe import _
from frappe.utils import flt
from frappe.model.document import Document


class SalesOrder(Document):
    def validate(self):
        self.merge_same_items()
        self.delete_empty_items()
        self.set_services_table()
        self.calculate()
        self.set_child_items()
        self.set_statuses()

    def merge_same_items(self):
        items_map = {}
        for idx, item in enumerate(self.items):
            items_map.setdefault(item.item_code, []).append(idx)

        to_remove = []
        for value in items_map.values():
            if len(value) > 1:
                full_qty = 0
                for d in value:
                    qty = self.items[d].qty
                    if qty > 0:
                        full_qty += qty
                self.items[value[0]].qty = full_qty
                for d in value[1:]:
                    to_remove.append(self.items[d])

        for d in to_remove:
            self.items.remove(d)

    def delete_empty_items(self):
        to_remove = []
        for d in self.items:
            if d.qty == 0:
                to_remove.append(d)

        for d in to_remove:
            self.items.remove(d)

    def set_services_table(self):
        if not self.get("services"):
            self.services = []
        for d in self.services:
            if not d.get("rate"):
                d.rate = 0

    def calculate(self):
        self.set_item_values()
        self.calculate_item_totals()
        self.calculate_service_amount()
        self.calculate_commission()
        self.calculate_total_amount()
        self.set_paid_and_pending_per_amount()

    def set_item_values(self):
        for d in self.items:
            doc = frappe.get_cached_doc("Item", d.item_code) # TODO: Not save to get value from cache in this case. Should clear all cache on update, probably
            d.item_name = doc.item_name
            if not self.from_not_received_items_to_sell:
                d.rate = doc.rate
            d.weight = doc.weight

            d.amount = d.rate * d.qty
            d.total_weight = d.weight * d.qty

    def calculate_item_totals(self):
        self.total_quantity, self.total_weight, self.items_cost = 0, 0, 0
        for d in self.items:
            self.total_quantity += d.qty
            self.total_weight += d.total_weight
            self.items_cost += d.amount

    def calculate_service_amount(self):
        self.service_amount = 0
        for d in self.services:
            self.service_amount += d.rate

    def calculate_commission(self):
        if self.edit_commission:
            r = calculate_commission(self.items_cost, self.commission)
        else:
            r = calculate_commission(self.items_cost)

        self.commission = r["commission"]
        self.margin = r["margin"]

    def calculate_total_amount(self):
        self.total_amount = (
            self.items_cost + self.margin + self.service_amount - self.discount
        )

    def set_paid_and_pending_per_amount(self):
        self.paid_amount = get_paid_amount(self.doctype, self.name)

        if int(self.total_amount) == 0:
            self.per_paid = 100
        else:
            self.per_paid = self.paid_amount / self.total_amount * 100

        self.pending_amount = self.total_amount - self.paid_amount

    def get_item_qty_map(self, split_combinations=False):
        item_qty_map = {}
        if split_combinations:
            parents = [d.parent_item_code for d in self.child_items]
            for d in self.items + self.child_items:
                if d.item_code not in parents:
                    if d.item_code not in item_qty_map:
                        item_qty_map[d.item_code] = 0
                    item_qty_map[d.item_code] += d.qty
        else:
            for d in self.items:
                if d.item_code not in item_qty_map:
                    item_qty_map[d.item_code] = 0
                item_qty_map[d.item_code] += d.qty
        return item_qty_map

    def set_child_items(self):
        self.child_items = []
        if len(self.items) == 0:
            return

        prepared_for_query = []
        for d in self.items:
            prepared_for_query.append(f'"{d.item_code}"')

        child_items = frappe.db.sql(
            """
            SELECT parent as parent_item_code, item_code, item_name, qty
            FROM `tabChild Item`
            WHERE parent IN (%s)
        """,
            values=(",".join(prepared_for_query),),
            as_dict=True,
        )

        item_qty_map = self.get_item_qty_map()
        for d in child_items:
            if d.parent_item_code in item_qty_map:
                d.qty = d.qty * item_qty_map[d.parent_item_code]

        self.extend("child_items", child_items)

    def set_statuses(self):
        self.set_delivery_status()
        self.set_payment_status()
        self.set_document_status()

    def set_payment_status(self):
        if self.docstatus == 2:
            return

        self.per_paid = int(self.per_paid)

        if self.per_paid > 100:
            status = "Overpaid"
        elif self.per_paid == 100:
            status = "Paid"
        elif self.per_paid > 0:
            status = "Partially Paid"
        else:
            status = "Unpaid"

        self.db_set("payment_status", status, update_modified=False)

    def set_delivery_status(self):
        if self.docstatus == 2 or self.delivery_status == "Delivered":
            return

        status = None

        po_name = frappe.get_all(
            "Purchase Order Sales Order",
            "parent",
            {"docstatus": 1, "sales_order_name": self.name},
        )
        if len(po_name) > 0:
            po_name = po_name[0].parent
            po_status = frappe.get_value("Purchase Order", po_name, "status")
            if po_status == "To Receive":
                status = "Purchased"
            elif po_status == "Completed":
                status = "To Deliver"

        if not status:
            status = "To Purchase"

        self.db_set("delivery_status", status, update_modified=False)

    def set_document_status(self):
        if self.docstatus == 0:
            status = "Draft"
        elif self.docstatus == 1:
            if self.payment_status == "Paid" and self.delivery_status == "Delivered":
                status = "Completed"
            else:
                status = "In Progress"
        else:
            status = "Cancelled"

        self.db_set("status", status, update_modified=False)

    def before_submit(self):
        self.edit_commission = True
        stock.sales_order_from_stock_submitted(self)

    @frappe.whitelist()
    def set_paid(self, paid_amount, cash):
        if int(self.total_amount) != 0:
            self.make_invoice_gl_entries(paid_amount, cash)

        self.set_paid_and_pending_per_amount()
        self.set_statuses()
        self.db_update()

    def make_invoice_gl_entries(self, paid_amount, cash=True):
        if paid_amount == 0:
            return

        if self.service_amount > 0:
            # TODO: Refactor, for now:
            # pyright: reportUnboundVariable=false
            sales_amt = self.items_cost + self.margin - self.discount
            service_amt_paid = 0
            if paid_amount > sales_amt:
                sales_amt_paid = sales_amt
                service_amt_paid = paid_amount - sales_amt
            else:
                sales_amt_paid = paid_amount
        else:
            sales_amt_paid = paid_amount

        make_gl_entry(self, get_account("cash" if cash else "bank"), paid_amount, 0)
        make_gl_entry(self, get_account("sales"), 0, sales_amt_paid)

        delivery_amt_paid, installation_amt_paid = 0, 0
        if self.service_amount > 0:
            delivery_amt, installation_amt = 0, 0
            for d in self.services:
                if "Delivery" in d.type:  # TODO: Test this with translation
                    delivery_amt += d.rate
                elif "Installation" in d.type:
                    installation_amt += d.rate

            if installation_amt == 0:  # TODO: Refactor
                delivery_amt_paid = service_amt_paid
            elif delivery_amt == 0:
                installation_amt_paid = service_amt_paid
            else:
                if delivery_amt_paid >= service_amt_paid:
                    delivery_amt_paid = service_amt_paid
                    installation_amt_paid = 0
                else:
                    delivery_amt_paid = delivery_amt
                    installation_amt_paid = service_amt_paid - delivery_amt_paid

            if delivery_amt_paid > 0:
                make_gl_entry(self, get_account("delivery"), 0, delivery_amt_paid)

            if installation_amt_paid > 0:
                make_gl_entry(
                    self, get_account("installation"), 0, installation_amt_paid
                )

        if (sales_amt_paid + delivery_amt_paid + installation_amt_paid) != paid_amount:
            frappe.throw(_("Cannot calculate amount for GL Entries properly"))

    @frappe.whitelist()
    def set_delivered(self):
        self.set_statuses()  # TODO: Is this really sets delivery status?
        self.db_update()  # TODO: Is it appropriate?
        if self.delivery_status == "Delivered":
            self.make_delivery_gl_entries()
            stock.sales_order_delivered(self)
        else:
            frappe.throw(_("Not able to set Delivered"))

    def make_delivery_gl_entries(self):
        delivery_accounts = get_account(["inventory", "cost_of_goods_sold"])
        make_gl_entries(
            self, delivery_accounts[0], delivery_accounts[1], self.items_cost
        )

    @frappe.whitelist()
    def split_combinations(self, combos_to_split, save):
        combos_to_split = list(set(combos_to_split))

        selected_child_items = [
            d for d in self.child_items if d.parent_item_code in combos_to_split
        ]

        to_remove = []
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
            child = frappe.get_doc(
                "Sales Order Item", {"parent": self.name, "item_code": d}
            )
            if child.docstatus == 1:
                child.cancel()
            child.delete()

        if save:
            self.save()

    def on_cancel(self):
        # TODO: Cancel payment and delivery
        # TODO: Update bin
        self.ignore_linked_doctypes = "GL Entry"

        make_reverse_gl_entry(self.doctype, self.name)

        self.set_paid_and_pending_per_amount()

        self.db_set("payment_status", "")
        self.db_set("delivery_status", "")

    def before_update_after_submit(self):
        if self.from_not_received_items_to_sell:
            self.flags.ignore_validate_update_after_submit = True
        self.validate()
CONDITIONS = [
    {"start": 0, "end": 9900, "commission_percentage": 15},
    {"start": 9901, "end": 19900, "commission_percentage": 13},
    {"start": 19901, "end": 39900, "commission_percentage": 11},
    {"start": 39901, "end": 49900, "commission_percentage": 9},
    {"start": 49901, "end": 69900, "commission_percentage": 7},
    {"start": 69901, "end": 1000000, "commission_percentage": 5},
]


@frappe.whitelist()
def calculate_commission(items_cost, commission=None):
    items_cost = flt(items_cost)
    if commission is not None:
        commission = float(commission)

    if items_cost <= 0:
        margin = 0
        commission = 0
    else:
        if commission is None:
            commission_percentages = []
            for condition in CONDITIONS:
                if condition["start"] <= items_cost <= condition["end"]:
                    commission_percentages.append(condition["commission_percentage"])
            # Check if rules only one condition is applied
            if len(commission_percentages) != 1:
                raise ValueError("Wrong conditions (applied more or less than 1 rule)")
            commission = commission_percentages[0]

        items_cost_rounding = round(items_cost, -1) - items_cost
        margin = round(items_cost * commission / 100, -1) + items_cost_rounding

    return {"commission": commission, "margin": margin}


@frappe.whitelist()
def get_sales_orders_in_purchase_order():
    return [
        d.sales_order_name
        for d in frappe.get_all("Purchase Order Sales Order", "sales_order_name")
    ]


@frappe.whitelist()
@frappe.validate_and_sanitize_search_inputs
def item_query(doctype, txt, searchfield, start, page_len, filters):
    from comfort.comfort.queries import default_query

    field = "from_actual_stock"
    if filters.get(field) is not None:
        if filters[field]:
            available_items = [
                d.item_code
                for d in frappe.get_all(
                    "Bin", "item_code", {"available_actual": [">", 0]}
                )
            ]
            filters["item_code"] = ["in", available_items]
        del filters[field]
    return default_query(doctype, txt, searchfield, start, page_len, filters)
