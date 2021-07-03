import frappe
from comfort.comfort.doctype.sales_order.sales_order import calculate_commission
from comfort.comfort.general_ledger import make_gl_entry
from frappe import _
from frappe.model.document import Document

item_doctype = "Sales Order Item"
child_item_doctype = "Sales Order Child Item"

# TODO: Deal with items to sell
# TODO: Queries impovement for SO (make it global)
# TODO: Bin
class Return(Document):
    @frappe.whitelist()
    def get_items(self):
        if self.voucher_type == "Sales Order":
            parents = [self.voucher_no]
        else:
            parents = frappe.get_all(
                "Purchase Order Sales Order",
                "sales_order_name",
                {"parent": self.voucher_no},
            )
            parents = [d.sales_order_name for d in parents]

        cur_child_items = []
        cur_items = []
        if hasattr(self, "items"):
            for d in self.items:
                if d.reference_doctype == child_item_doctype:
                    cur_child_items.append(d.reference_name)
                elif d.reference_doctype == item_doctype:
                    cur_items.append(d.reference_name)

        items = frappe.get_all(
            item_doctype,
            [
                "name",
                "item_code",
                "item_name",
                "qty",
                "rate",
                "parent AS sales_order",
                f"'{item_doctype}' AS doctype",
            ],
            {
                "parent": ["in", parents],
                "name": ["not in", cur_items],
            },
        )

        if self.split_combinations:
            child_items = frappe.get_all(
                child_item_doctype,
                [
                    "name",
                    "item_code",
                    "item_name",
                    "qty",
                    "parent_item_code",
                    "parent AS sales_order",
                    f"'{child_item_doctype}' AS doctype",
                ],
                {
                    "parent": ["in", parents],
                    "name": ["not in", cur_child_items],
                },
            )
            rates = frappe.get_all(
                "Item",
                ["item_code", "rate"],
                {"item_code": ["in", [d.item_code for d in child_items]]},
            )
            rates_map = {}
            for d in rates:
                rates_map[d.item_code] = d.rate

            parent_items = []
            for d in child_items:
                parent_items.append(d.parent_item_code)
                d.rate = rates_map.get(d.item_code) or 0
                d.doctype = child_item_doctype

            items = [d for d in items if d.item_code not in parent_items]

            items += child_items
        return items

    @frappe.whitelist()
    def add_items(self, items):
        items_cost = 0
        for d in items:
            self.append(
                "items",
                {
                    "item_code": d["item_code"],
                    "item_name": d["item_name"],
                    "qty": d["qty"],
                    "sales_order": d["sales_order"],
                    "rate": d["rate"],
                    "reference_doctype": d["doctype"],
                    "reference_name": d["name"],
                },
            )
            items_cost += d["rate"]
        commission = frappe.get_cached_value(
            self.voucher_type, self.voucher_no, "commission"
        )
        commission, margin = calculate_commission(items_cost, commission).values()
        self.amount_to_pay = items_cost + margin
        self.amount_to_receive = items_cost

    def validate(self):
        if self.money_to_clients and (
            not self.get("amount_to_pay") or self.amount_to_pay == 0
        ):
            frappe.throw(_("Set Amount to Pay"))

        if self.money_from_supplier and (
            not self.get("amount_to_receive") or self.amount_to_receive == 0
        ):
            frappe.throw(_("Set Amount to Receive"))

        if (self.items_from_clients or self.items_to_supplier) and (
            not self.get("items") or len(self.items) == 0
        ):
            frappe.throw(_("Set Items"))

        for d in self.items:
            if not (d.reference_doctype or d.reference_name):
                frappe.throw(
                    _("No reference name or doctype for item: {0}").format(d.item_code)
                )

        if self.items_to_supplier:
            self.items_from_clients = True

    def before_submit(self):
        self.delete_items_from_sales_orders()
        self.delete_items_from_purchase_order()

        self.make_purchase_invoice_gl_entries()
        self.make_purchase_delivery_gl_entries()

        self.make_sales_invoice_gl_entries()
        self.make_sales_delivery_gl_entries()

        self.update_bin()

    def delete_items_from_sales_orders(self):
        if not self.items_from_clients:
            return

        orders_to_items = {}
        for d in self.items:
            if d.sales_order not in orders_to_items:
                orders_to_items[d.sales_order] = {}
            if d.item_code in orders_to_items[d.sales_order]:
                orders_to_items[d.sales_order][d.item_code].qty += d.qty
            orders_to_items[d.sales_order][d.item_code] = d

        for order_name, cur_items in orders_to_items.items():
            doc = frappe.get_doc("Sales Order", order_name)
            doc.flags.ignore_validate_update_after_submit = True

            child_item_names = [
                d.reference_name
                for d in cur_items.values()
                if d.reference_doctype == child_item_doctype
            ]

            doc.split_combinations(
                [
                    d.parent_item_code
                    for d in doc.child_items
                    if d.name in child_item_names
                ],
                save=False,
            )

            item_codes = list(cur_items.keys())
            for d in doc.items:
                if d.item_code in item_codes:
                    d.qty -= cur_items[d.item_code].qty

            doc.validate()
            if not doc.items or len(doc.items) == 0:
                doc.reload()
                doc.flags.ignore_links = True
                doc.cancel()
            else:
                doc.save()

    def delete_items_from_purchase_order(self):
        if self.voucher_type != "Purchase Order" or not self.items_to_supplier:
            return

        doc = frappe.get_doc("Purchase Order", self.voucher_no)
        doc.flags.ignore_links = True
        doc.validate()
        doc.db_update_all()

    def make_purchase_invoice_gl_entries(self):
        if self.voucher_type != "Purchase Order" or not self.money_from_supplier:
            return

        transaction_type = "Invoice"

        company = frappe.db.get_single_value("Defaults", "default_company")

        expense_account = frappe.db.get_value(
            "Company", company, "stock_received_but_not_billed"
        )

        doc = frappe.get_doc("Purchase Order", self.voucher_no)
        make_gl_entry(doc, expense_account, 0, self.amount_to_receive, transaction_type)

        credit_to = frappe.db.get_value("Company", company, "default_bank_account")
        make_gl_entry(doc, credit_to, self.amount_to_receive, 0, transaction_type)

    def make_purchase_delivery_gl_entries(self):
        if self.voucher_type != "Purchase Order" or not self.items_to_supplier:
            return

        company = frappe.db.get_single_value("Defaults", "default_company")

        expense_account = frappe.db.get_value(
            "Company", company, "default_inventory_account"
        )
        make_gl_entry(self, expense_account, 0, self.amount_to_receive, "Delivery")

        credit_to = frappe.db.get_value(
            "Company", company, "stock_received_but_not_billed"
        )
        make_gl_entry(self, credit_to, self.amount_to_receive, 0, "Delivery")

    def make_sales_invoice_gl_entries(self):
        if not self.money_to_clients:
            return

        transaction_type = "Invoice"

        company = frappe.db.get_single_value("Defaults", "default_company")

        income_account = frappe.db.get_value(
            "Company", company, "default_income_account"
        )
        debit_to = frappe.db.get_value("Company", company, "default_bank_account")

        self.sales_order_map = self.get_sales_orders_map_for_gl_entries()

        for doc, amount in self.get_sales_orders_map_for_gl_entries():
            if doc.docstatus == 1:
                make_gl_entry(doc, income_account, amount, 0, transaction_type)
                make_gl_entry(doc, debit_to, 0, amount, transaction_type)

    def make_sales_delivery_gl_entries(self):
        if not self.items_from_clients:
            return

        transaction_type = "Delivery"

        company = frappe.db.get_single_value("Defaults", "default_company")

        income_account = frappe.db.get_value(
            "Company", company, "default_inventory_account"
        )
        debit_to = frappe.db.get_value(
            "Company", company, "default_cost_of_goods_sold_account"
        )

        if not self.sales_order_map:
            self.sales_order_map = self.get_sales_orders_map_for_gl_entries()

        for doc, amount in self.sales_order_map:
            if doc.docstatus == 1:
                make_gl_entry(doc, income_account, amount, 0, transaction_type)
                make_gl_entry(doc, debit_to, 0, amount, transaction_type)

    def get_sales_orders_map_for_gl_entries(self):
        sales_order_amount_map = {}
        for d in self.items:
            if not d.sales_order in sales_order_amount_map:
                sales_order_amount_map[d.sales_order] = 0
            sales_order_amount_map[d.sales_order] += d.qty * d.rate

        gl_entries_raw = []
        for order_name, amount in sales_order_amount_map.items():
            doc: frappe._dict = frappe.get_value(
                "Sales Order", order_name, ["customer", "docstatus"], as_dict=True
            )
            doc.doctype = "Sales Order"
            doc.name = order_name
            doc.posting_date = self.posting_date
            gl_entries_raw.append((doc, amount))
        return gl_entries_raw
