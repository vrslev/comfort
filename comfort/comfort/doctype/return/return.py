import frappe
from comfort.comfort.doctype.purchase_order.purchase_order import PurchaseOrder
from comfort.comfort.doctype.sales_order.sales_order import calculate_commission
from comfort.comfort.general_ledger import (
    get_account,
    get_paid_amount,
    make_gl_entries,
)
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

        if self.voucher_type == "Sales Order":
            self.amount = items_cost + margin
        else:
            self.amount = items_cost

    def validate(self):
        if self.return_money and (not self.get("amount") or self.amount == 0):
            frappe.throw(_("Set Amount"))

        if self.return_items and (not self.get("items") or len(self.items) == 0):
            frappe.throw(_("Set Items"))

        for d in self.items:
            if not (d.reference_doctype or d.reference_name):
                frappe.throw(
                    _("No reference name or doctype for item: {0}").format(d.item_code)
                )

        # if self.voucher_type == "Sales Order" and self.return_items:
        #     self.return_money = True

    def before_submit(self):
        self.created_sales_orders = []
        is_po = self.voucher_type == "Purchase Order"

        if is_po:
            self.make_purchase_return()
        else:
            items = self.get_sales_order_item_map()[self.voucher_no].values()
            amount = self.get_items_amount(items)
            self.make_sales_return(self.voucher_no, items, amount, False)

        self.update_bin()

    def make_purchase_return(self):
        if self.voucher_type != "Purchase Order":
            return

        is_received = (
            frappe.get_value(self.voucher_type, self.voucher_no, "status")
            == "Completed"
        )

        # Compensation
        if self.return_money and not self.return_items:
            accounts = ["purchase_compensations", "cash"]

        elif self.return_money and self.return_items:
            accounts = [
                "inventory"
                if is_received  # Defect
                else "prepaid_inventory",  # Initiated by supplier
                "cash",
            ]
            self.return_sales_orders()
            self.update_purchase_order()

        elif not self.return_money and self.return_items:
            if is_received:  # Defect
                accounts = ["inventory", "prepaid_inventory"]
                self.return_sales_orders()
                self.update_purchase_order()
                self.create_new_paid_purchase_order()

            else:
                frappe.throw(
                    _(
                        "Cannot return items without money when Purchase Order is not received"
                    )
                )
        else:
            frappe.throw("")

        accounts = get_account(accounts)

        make_gl_entries(
            frappe._dict({"doctype": self.voucher_type, "name": self.voucher_no}),
            accounts[0],
            accounts[1],
            self.amount,
        )

    def get_sales_order_item_map(self):
        orders_to_items = {}
        for d in self.items:
            if d.sales_order not in orders_to_items:
                orders_to_items[d.sales_order] = {}
            if d.item_code not in orders_to_items[d.sales_order]:
                orders_to_items[d.sales_order][d.item_code] = d
            orders_to_items[d.sales_order][d.item_code].qty += d.qty

        return orders_to_items

    def get_items_amount(self, items):
        amount = 0
        for d in items:
            amount += d.qty * d.rate
        return amount

    def return_sales_orders(self):
        if not self.voucher_type == "Purchase Order":
            return

        orders_to_items = self.get_sales_order_item_map()
        for order_name, cur_items in orders_to_items.items():
            items = cur_items.values()
            amount = self.get_items_amount(items)
            self.make_sales_return(order_name, items, amount, True)

    def make_sales_return(self, order_name, items, amount, from_purchase_return=False):
        doc = frappe.get_doc("Sales Order", order_name)

        if doc.docstatus == 2:
            return

        def validate_paid_amt():
            paid_amount = get_paid_amount(doc.doctype, doc.name)
            if amount > paid_amount:
                frappe.throw(
                    _(f"Cannot return Amount greater than Paid Amount ({doc.name})")
                )

        # Compensation
        if self.return_money and not self.return_items:
            validate_paid_amt()
            accounts = get_account(["cash", "sales_compensations"])
            make_gl_entries(doc, accounts[0], accounts[1], amount)

        elif (self.return_money and self.return_items) or from_purchase_return:
            # Initiated by customer or Purchase Return
            if doc.delivery_status == "Delivered" or from_purchase_return:
                validate_paid_amt()

                self.split_order(
                    doc, items, amount, create_new_doc=from_purchase_return
                )

                sales_accounts = get_account(["cash", "sales"])
                make_gl_entries(doc, sales_accounts[0], sales_accounts[1], amount)

                if doc.service_amount:
                    delivery_accounts = get_account(["cash", "delivery"])
                    make_gl_entries(
                        doc,
                        delivery_accounts[0],
                        delivery_accounts[1],
                        doc.service_amount,
                    )

                # TODO: Continue after creating Services table
                # installation_accounts = get_default_accounts(["cash", "installation"])
                # make_gl_entries(
                #     doc, installation_accounts[0], installation_accounts[1], amount
                # )

                inventory_accounts = get_account(
                    ["cost_of_goods_sold", "inventory"]
                )
                make_gl_entries(
                    doc, inventory_accounts[0], inventory_accounts[1], amount
                )

            else:
                frappe.throw(
                    _(
                        f"Cannot return items when Sales Order is not delivered: ({doc.name})"
                    )
                )

        else:
            frappe.throw("")

    def split_order(self, doc, items, amount, create_new_doc):
        doc.flags.ignore_validate_update_after_submit = True

        child_item_names = [
            d.reference_name for d in items if d.reference_doctype == child_item_doctype
        ]
        doc.split_combinations(
            [d.parent_item_code for d in doc.child_items if d.name in child_item_names],
            save=False,
        )

        item_codes = []
        items_map = {}
        for d in items:
            if d.item_code not in items_map:
                items_map[d.item_code] = 0
            items_map[d.item_code] += d.qty

            item_codes.append(d.item_code)

        items_for_new_order = {}

        for d in doc.items:
            if d.item_code in item_codes:
                cur_qty = items_map[d.item_code]
                d.qty -= cur_qty

                if d.item_code not in items_for_new_order:
                    items_for_new_order[d.item_code] = 0
                items_for_new_order[d.item_code] += cur_qty

        doc.validate()
        if not doc.items or len(doc.items) == 0:
            doc.reload()
            doc.flags.ignore_links = True
            doc.cancel()
        else:
            doc.edit_commission = True
            doc.save()

        if create_new_doc:
            new_doc = frappe.get_doc(
                {
                    "doctype": "Sales Order",
                    "customer": doc.customer,
                    "items": [
                        {"item_code": key, "qty": value}
                        for key, value in items_for_new_order.items()
                    ],
                    "commission": doc.commission,
                    "edit_commission": True,
                }
            )
            new_doc.insert()
            new_doc.make_invoice_gl_entries(amount)
            new_doc.save()

            self.created_sales_orders.append(new_doc.name)

    def get_items_for_sales_return(self):
        items_map = {}
        for d in self.items:
            if d.item_code in items_map:
                items_map[d.item_code].qty += d.qty
            items_map[d.item_code] = d
        return items_map.values()

    def update_purchase_order(self):
        if not (self.voucher_type == "Purchase Order" and self.return_items):
            return

        doc = frappe.get_doc("Purchase Order", self.voucher_no)
        # doc.flags.ignore_links = True
        doc.flags.ignore_validate_update_after_submit = True
        doc.validate()
        # doc.flags.ignore_links = True
        doc.save()

        # doc.validate()
        # doc.db_update_all()

    def create_new_paid_purchase_order(self):
        if (
            not hasattr(self, "created_sales_orders")
            or len(self.created_sales_orders) == 0
        ):
            return

        doc: PurchaseOrder = frappe.get_doc(
            {
                "doctype": "Purchase Order",
                "sales_orders": [
                    {"sales_order_name": d} for d in self.created_sales_orders
                ],
            }
        ).insert()
        doc.make_invoice_gl_entries()
        doc.save()
        return doc.name

    def update_bin(self):
        pass
