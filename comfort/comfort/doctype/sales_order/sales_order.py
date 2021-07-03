import frappe
from comfort.comfort.general_ledger import make_gl_entry, make_reverse_gl_entry
from frappe import _
from frappe.model.document import Document


class SalesOrder(Document):
    # TODO: Item query
    # TODO: Make returns
    # TODO: Services
    # TODO: Hide button "DELIVERED" when PO not recevied yet
    # TODO: Make GL Entries to all kinds of stuff
    # TODO: Calculate quantity by child items (by package)
    # TODO: Automatically allocate GL Entries without voucher (so return could work)
    def validate(self):  # TODO: Validate Items length == 0
        self.merge_same_items()
        self.delete_empty_items()
        self.calculate()
        self.set_child_items()
        self.set_statuses()

    def merge_same_items(self):  # TODO: Test this
        items_map = {}
        for idx, item in enumerate(self.items):
            items_map.setdefault(item.item_code, []).append(idx)

        to_remove = []
        for value in items_map.values():
            if len(value) > 1:
                full_qty = 0
                for d in value:
                    full_qty += self.items[d].qty
                self.items[value[0]].qty = full_qty
                for d in value[1:]:
                    to_remove.append(self.items[d])

        for d in to_remove:
            self.items.remove(d)

    def delete_empty_items(self):
        to_remove = []
        for d in self.items:
            if d.qty <= 0:
                to_remove.append(d)

        for d in to_remove:
            self.items.remove(d)

    def calculate(self):
        self.set_item_rate_amount()
        self.calculate_item_totals()
        self.calculate_commission_and_totals()
        self.set_paid_and_pending_per_amount()

    def set_item_rate_amount(self):
        for d in self.items:
            doc = frappe.get_cached_doc("Item", d.item_code)
            d.rate = doc.rate
            d.amount = d.rate * d.qty
            d.weight = doc.weight
            d.total_weight = d.weight * d.qty

    def calculate_item_totals(self):
        self.total_quantity, self.total_weight, self.items_cost = 0, 0, 0
        for d in self.items:
            self.total_quantity += d.qty
            self.total_weight += d.total_weight
            self.items_cost += d.amount

    def calculate_commission_and_totals(self):
        if self.edit_commission:
            r = calculate_commission(self.items_cost, self.commission)
        else:
            r = calculate_commission(self.items_cost)

        self.margin = r["margin"]
        self.commission = r["commission"]

        self.total_amount = self.items_cost + self.margin - self.discount

    def set_paid_and_pending_per_amount(self, additional_paid_amount=0):
        self.db_set("paid_amount", self.paid_amount + additional_paid_amount)

        if int(self.total_amount) == 0:
            per_paid = 100
        else:
            per_paid = self.paid_amount / self.total_amount * 100
        self.db_set("per_paid", per_paid)
        self.db_set("pending_amount", self.total_amount - self.paid_amount)

    def set_child_items(self):
        self.child_items = []
        if len(self.items) == 0:
            return

        items_to_qty_map = {}
        prepared_for_query = []
        for d in self.items:
            prepared_for_query.append(f'"{d.item_code}"')
            if d.item_code not in items_to_qty_map:
                items_to_qty_map[d.item_code] = 0
            items_to_qty_map[d.item_code] += d.qty

        child_items = frappe.db.sql(
            f"""
            SELECT parent as parent_item_code, item_code, item_name, qty
            FROM `tabChild Item`
            WHERE parent IN ({','.join(prepared_for_query)})
        """,
            as_dict=True,
        )

        for d in child_items:
            if d.parent_item_code not in items_to_qty_map:
                continue
            d.qty = d.qty * items_to_qty_map[d.parent_item_code]

        self.extend("child_items", child_items)

    def set_statuses(self):
        self.set_delivery_status()
        self.set_payment_status()
        self.set_status()

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

        self.db_set("payment_status", status)

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
            po_status = frappe.get_cached_value("Purchase Order", po_name, "status")
            if po_status == "To Receive":
                status = "Purchased"
            elif po_status == "Completed":
                status = "To Deliver"

        if not status:
            status = "To Purchase"

        self.db_set("delivery_status", status)

    def set_status(self):
        if self.docstatus == 0:
            status = "Draft"
        elif self.docstatus == 1:
            if self.payment_status == "Paid" and self.delivery_status == "Delivered":
                status = "Completed"
            else:
                status = "In Progress"
        else:
            status = "Cancelled"

        self.db_set("status", status)

    def make_delivery_gl_entries(self):
        transaction_type = "Delivery"
        if frappe.db.exists(
            {
                "doctype": "GL Entry",
                "transaction_type": transaction_type,
                "voucher_type": self.doctype,
                "voucher_no": self.name,
            }
        ):
            frappe.throw(_("Already marked as delivered"))

        company = frappe.db.get_single_value("Defaults", "default_company")

        income_account = frappe.db.get_value(
            "Company", company, "default_inventory_account"
        )
        make_gl_entry(self, income_account, 0, self.total_amount, transaction_type)

        debit_to = frappe.db.get_value(
            "Company", company, "default_cost_of_goods_sold_account"
        )
        make_gl_entry(self, debit_to, self.total_amount, 0, transaction_type)

    def update_actual_qty(self):
        items_map = {}
        for d in self.items:
            if d.item_code not in items_map:
                items_map[d.item_code] = 0
            items_map[d.item_code] += d.qty

        for item_code, qty in items_map.items():
            bin = frappe.get_doc("Bin", item_code)
            bin.actual_qty -= qty
            bin.save()

    @frappe.whitelist()
    def set_delivered(self):
        self.make_delivery_gl_entries()
        self.update_actual_qty()
        self.db_set("delivery_status", "Delivered")

    def make_invoice_gl_entries(self, paid_amount):
        transaction_type = "Invoice"

        company = frappe.db.get_single_value("Defaults", "default_company")

        income_account = frappe.db.get_value(
            "Company", company, "default_income_account"
        )
        make_gl_entry(self, income_account, 0, paid_amount, transaction_type)

        debit_to = frappe.db.get_value("Company", company, "default_bank_account")
        make_gl_entry(self, debit_to, paid_amount, 0, transaction_type)

    @frappe.whitelist()
    def set_paid(self, paid_amount):
        if int(self.total_amount) != 0:
            self.make_invoice_gl_entries(paid_amount)

        self.set_paid_and_pending_per_amount(paid_amount)
        self.set_payment_status()

    def on_cancel(self):
        self.ignore_linked_doctypes = "GL Entry"

        make_reverse_gl_entry(self.doctype, self.name, "Delivery")
        make_reverse_gl_entry(self.doctype, self.name, "Invoice")

        self.set_paid_and_pending_per_amount(-self.paid_amount)

        self.db_set("payment_status", "")
        self.db_set("delivery_status", "")

    @frappe.whitelist()
    def split_combinations(self, combos_to_split, save):

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
                {
                    "item_code": d.item_code,
                    "item_name": d.item_name,
                    "qty": d.qty,
                },
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
    items_cost = float(items_cost)
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

    return {
        "commission": commission,
        "margin": margin,
    }


@frappe.whitelist()
def get_sales_orders_in_purchase_order():
    return [
        d.sales_order_name
        for d in frappe.get_all("Purchase Order Sales Order", "sales_order_name")
    ]
