import re

from ikea_api import (
    Cart,
    OrderCapture,
    Purchases,
    get_authorized_token,
    get_guest_token,
)
from ikea_api.errors import NoDeliveryOptionsAvailableError, WrongItemCodeError
from ikea_api_parser import DeliveryOptions, PurchaseHistory, PurchaseInfo

from comfort.comfort.general_ledger import (
    get_account,
    get_paid_amount,
    make_gl_entries,
    make_reverse_gl_entry,
)
import frappe
from frappe import _, as_json
from frappe.model.document import Document
from frappe.utils import parse_json
from frappe.utils.data import add_to_date, get_datetime, getdate, now_datetime, today
from frappe.utils.password import get_decrypted_password

# TODO: Create SERVICES Account


class PurchaseOrder(Document):
    def autoname(self):
        months = {
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
        this_month = months[now_datetime().month].title()
        carts_in_this_month = frappe.db.sql(
            """
            SELECT name from `tabPurchase Order`
            WHERE name LIKE '{}-%'
            ORDER BY CAST(REGEXP_SUBSTR(name, '[0-9]+$') as int) DESC
            """.format(
                this_month
            )
        )
        if carts_in_this_month:
            latest_cart_name = carts_in_this_month[0][0]
            latest_cart_name_no_ = re.findall(r"-(\d+)", latest_cart_name)
            if len(latest_cart_name_no_) > 0:
                latest_cart_name_no = latest_cart_name_no_[0]
            cart_no = int(latest_cart_name_no) + 1
        else:
            cart_no = 1

        self.name = f"{this_month}-{cart_no}"

    def before_insert(self):
        self.status = "Draft"

    def validate(self):
        self.validate_empty()
        self.delete_sales_order_dublicates()
        self.set_customer_and_total_in_sales_orders()
        self.calculate_totals()

    def validate_empty(self):
        if not (self.sales_orders or self.items_to_sell):
            frappe.throw("Добавьте заказы или товары на продажу")

    def delete_sales_order_dublicates(self):
        # TODO: Check if there any IkeaCarts that contains those Sales Orders
        sales_order_names = list({s.sales_order_name for s in self.sales_orders})
        sales_orders_no_dublicates = []

        for s in self.sales_orders:
            if s.sales_order_name in sales_order_names:
                sales_orders_no_dublicates.append(s)
                sales_order_names.remove(s.sales_order_name)

        self.sales_orders = sales_orders_no_dublicates

    def set_customer_and_total_in_sales_orders(self):
        for d in self.sales_orders:
            d.customer, total, status = frappe.get_value(
                "Sales Order",
                d.sales_order_name,
                ("customer", "total_amount", "docstatus"),
            )
            d.total = total if status != 2 else 0

    def calculate_totals(self):
        (
            self.total_weight,
            self.total_amount,
            self.sales_order_cost,
            self.items_to_sell_cost,
        ) = (0, 0, 0, 0)

        so_items = frappe.get_all(
            "Sales Order Item",
            filters={
                "parent": ["in", [d.sales_order_name for d in self.sales_orders]],
                "docstatus": ["!=", 2],
            },
            fields=[
                f"SUM(qty * rate) AS sales_order_cost",
                "SUM(total_weight) AS total_weight",
            ],
        )[0]

        self.sales_order_cost = (
            so_items.sales_order_cost if so_items.sales_order_cost else 0
        )
        self.total_weight = so_items.total_weight if so_items.total_weight else 0

        for d in self.items_to_sell:
            self.items_to_sell_cost += d.rate * d.qty
            self.total_weight += d.weight * d.qty

        self.total_amount = self.sales_order_cost + self.items_to_sell_cost
        if self.delivery_cost:
            self.total_amount += self.delivery_cost
        else:
            self.delivery_cost = 0

    def before_save(self):
        if self.docstatus == 0:
            self.get_delivery_services()

    def get_delivery_services(self):
        try:
            templated_items = self.get_templated_items_for_api(True)
            delivery_services = IkeaCartUtils().get_delivery_services(templated_items)
            self.update(
                {
                    "delivery_options": delivery_services["options"],
                    "cannot_add_items": as_json(delivery_services["cannot_add"])
                    if delivery_services["cannot_add"]
                    else None,
                }
            )
        except Exception as e:
            frappe.msgprint("\n".join([str(d) for d in e.args]), _("Error"))

    @frappe.whitelist()
    def checkout(self):
        items = self.get_templated_items_for_api(False)
        u = IkeaCartUtils()
        return [u.add_items_to_cart_authorized(items)]

    def get_templated_items_for_api(self, split_combinations=False):
        all_items = []
        all_items += self.items_to_sell  # TODO: Check if there's product bundle

        if self.sales_orders and len(self.sales_orders) > 0:
            sales_order_names = [d.sales_order_name for d in self.sales_orders]
            so_items = frappe.db.sql(
                """
                SELECT name, item_code, qty
                FROM `tabSales Order Item`
                WHERE parent IN %(sales_orders)s
                AND qty > 0
            """,
                {"sales_orders": sales_order_names},
                as_dict=True,
            )

            if split_combinations:
                packed_items = frappe.db.sql(
                    """
                    SELECT parent_item_code, item_code, qty
                    FROM `tabSales Order Child Item`
                    WHERE parent IN %(sales_orders)s
                    AND qty > 0
                """,
                    {"sales_orders": sales_order_names},
                    as_dict=True,
                )
                all_items += packed_items

                parent_items = [d.parent_item_code for d in packed_items]
                so_items = [d for d in so_items if d.item_code not in parent_items]

            all_items += so_items

        templated_items = {}
        for d in all_items:
            d.item_code = str(d.item_code)
            if d.item_code not in templated_items:
                templated_items[d.item_code] = 0
            templated_items[d.item_code] += int(d.qty)

        return templated_items

    def before_submit(self):
        self.delivery_options = []
        self.cannot_add_items = None

    def make_invoice_gl_entries(self):
        already_paid_amount = get_paid_amount(self.doctype, self.name)

        if self.total_amount != already_paid_amount:
            if self.delivery_cost > 0:
                amt_to_pay = self.total_amount - already_paid_amount
                amt_without_delivery = self.sales_order_cost + self.items_to_sell_cost
                delivery_amt_paid = 0
                if amt_to_pay > amt_without_delivery:
                    delivery_amt_paid = amt_to_pay - amt_without_delivery
                    inventory_amt_paid = amt_without_delivery
                else:
                    inventory_amt_paid = amt_to_pay
            else:
                inventory_amt_paid = self.total_amount - already_paid_amount

            inventory_accounts = get_account(["cash", "prepaid_inventory"])
            make_gl_entries(
                self, inventory_accounts[0], inventory_accounts[1], inventory_amt_paid
            )

            if self.delivery_cost > 0:
                delivery_accounts = get_account(["cash", "purchase_delivery"])
                make_gl_entries(
                    self, delivery_accounts[0], delivery_accounts[1], delivery_amt_paid
                )

    @frappe.whitelist()
    def before_submit_events(
        self, purchase_id, purchase_info_loaded, purchase_info, delivery_cost=None
    ):
        self.order_confirmation_no = purchase_id

        if purchase_info_loaded:
            self.schedule_date = getdate(purchase_info["delivery_date"])
            self.posting_date = getdate(purchase_info["purchase_date"])
            self.delivery_cost = purchase_info["delivery_cost"]
            items_cost = purchase_info["items_cost"]

        else:
            self.schedule_date = add_to_date(None, weeks=2)
            self.posting_date = today()
            self.delivery_cost = delivery_cost
            items_cost = self.total_amount

        if len(self.sales_orders) > 0:
            for ikea_cart_so in self.sales_orders:
                sales_order = frappe.get_doc(
                    "Sales Order", ikea_cart_so.sales_order_name
                )
                sales_order.submit()

        if self.total_amount != items_cost:
            # TODO: Ideally—edit all items in Sales Orders instead of applying this mock discount
            self.difference = self.total_amount - items_cost

        self.calculate_totals()
        self.make_invoice_gl_entries()
        self.status = "To Receive"
        self.submit()

    def update_purchased_qty(self):
        so_items = self.get_sales_order_items_for_bin()
        for item_code, qty in so_items:
            bin = frappe.get_doc("Bin", item_code)
            bin.reserved_purchased += qty
            bin.save()

        items_to_sell = self.get_items_to_sell_for_bin()
        for item_code, qty in items_to_sell:
            bin = frappe.get_doc("Bin", item_code)
            bin.available_purchased += qty
            bin.save()

    def get_sales_order_items_for_bin(
        self,
    ):  # TODO: use templated items instead (one that generates for cart)
        if not self.sales_orders and len(self.sales_orders) > 0:
            return
        sales_order_names = [d.sales_order_name for d in self.sales_orders]
        so_items = frappe.db.sql(
            """
            SELECT item_code, qty
            FROM `tabSales Order Item`
            WHERE parent IN %(sales_orders)s
            AND qty > 0
        """,
            {"sales_orders": sales_order_names},
            as_dict=True,
        )

        packed_items = frappe.db.sql(
            """
            SELECT parent_item_code, item_code, qty
            FROM `tabSales Order Child Item`
            WHERE parent IN %(sales_orders)s
            AND qty > 0
        """,
            {"sales_orders": sales_order_names},
            as_dict=True,
        )

        parent_items = [d.parent_item_code for d in packed_items]
        so_items = [d for d in so_items if d.item_code not in parent_items]

        items = packed_items + so_items

        items_map = {}
        for d in items:
            if d.item_code not in items_map:
                items_map[d.item_code] = 0
            items_map[d.item_code] += d.qty

        return items_map.items()

    def get_items_to_sell_for_bin(self):
        items_map = {}
        for d in self.items_to_sell:
            if d.item_code not in items_map:
                items_map[d.item_code] = 0
            items_map[d.item_code] += d.qty
        return items_map.items()

    def update_status_in_sales_orders(self):
        for d in self.sales_orders:
            frappe.get_doc("Sales Order", d.sales_order_name).set_statuses()

    def on_submit(self):
        self.update_purchased_qty()
        self.update_status_in_sales_orders()

    @frappe.whitelist()
    def set_completed(self):
        self.make_delivery_gl_entries()
        self.update_actual_qty()
        self.db_set("status", "Completed")

    def make_delivery_gl_entries(self):
        accounts = get_account(["prepaid_inventory", "inventory"])
        make_gl_entries(
            self,
            accounts[0],
            accounts[1],
            self.items_to_sell_cost + self.sales_order_cost,
        )

    def update_actual_qty(self):
        so_items = self.get_sales_order_items_for_bin()
        for item_code, qty in so_items:
            bin = frappe.get_doc("Bin", item_code)
            bin.reserved_purchased -= qty
            bin.reserved_actual += qty
            bin.save()

        items_to_sell = self.get_items_to_sell_for_bin()
        for item_code, qty in items_to_sell:
            bin = frappe.get_doc("Bin", item_code)
            bin.available_purchased -= qty
            bin.available_actual += qty
            bin.save()

    def on_cancel(self):
        self.ignore_linked_doctypes = "GL Entry"
        make_reverse_gl_entry(self.doctype, self.name)
        self.update_status_in_sales_orders()
        # TODO: UPDATE BIN


class IkeaCartUtils:
    def __init__(self):
        settings = frappe.get_single("Ikea Cart Settings")
        self.zip_code = settings.zip_code
        self.username = settings.username
        self.password = get_decrypted_password(
            "Ikea Cart Settings", "Ikea Cart Settings", raise_exception=False
        )
        self.guest_token = settings.guest_token
        self.authorized_token = settings.authorized_token

    def get_token(self, authorize=False):
        from datetime import datetime

        doc = frappe.get_single("Ikea Cart Settings")
        if not authorize:
            guest_token_expiration_time: datetime = get_datetime(
                doc.guest_token_expiration_time
            )
            if not self.guest_token or guest_token_expiration_time <= now_datetime():
                self.guest_token = get_guest_token()
                doc.guest_token = self.guest_token
                doc.guest_token_expiration_time = add_to_date(None, hours=720)
                doc.save()
                frappe.db.commit()
            return self.guest_token
        else:
            authorized_token_expiration_time: datetime = get_datetime(
                doc.authorized_token_expiration_time
            )
            if (
                not self.authorized_token
                or authorized_token_expiration_time <= now_datetime()
            ):
                if not self.username and not self.password:
                    frappe.throw("Введите логин и пароль в настройках")
                self.authorized_token = get_authorized_token(
                    self.username, self.password
                )
                doc.authorized_token = self.authorized_token
                doc.authorized_token_expiration_time = add_to_date(None, hours=24)
                doc.save()
                frappe.db.commit()
            return self.authorized_token

    def get_delivery_services(self, items):
        self.get_token()
        adding = self.add_items_to_cart(self.guest_token, items)
        order_capture = OrderCapture(self.guest_token, self.zip_code)
        try:
            response = order_capture.get_delivery_services()
            parsed = DeliveryOptions(response).parse()
            return {"options": parsed, "cannot_add": adding["cannot_add"]}
        except NoDeliveryOptionsAvailableError:
            frappe.msgprint(
                "Нет доступных способов доставки", alert=True, indicator="red"
            )

    def add_items_to_cart(self, token, items):
        cart = Cart(token)
        cart.clear()
        res = {"cannot_add": [], "message": None}
        while True:
            try:
                res["message"] = cart.add_items(items)
                break
            except WrongItemCodeError as e:
                [items.pop(i) for i in e.args[0]]
                if not res["cannot_add"]:
                    res["cannot_add"] = []
                res["cannot_add"] += e.args[0]
        return res

    def add_items_to_cart_authorized(self, items):
        token = self.get_token(authorize=True)
        self.add_items_to_cart(token, items)
        return Cart(token).show()

    def get_purchase_history(self):
        token = self.get_token(authorize=True)
        purchases = Purchases(token)
        response = purchases.history()
        return PurchaseHistory(response).parse()

    def get_purchase_info(self, purchase_id, use_lite_id=False):
        token = self.get_token(authorize=True)
        purchases = Purchases(token)
        email = self.username if use_lite_id else None
        response = purchases.order_info(purchase_id, email=email)
        return PurchaseInfo(response).parse()


@frappe.whitelist()
def get_sales_orders_containing_items(items_in_options, sales_orders):
    items_in_options = parse_json(items_in_options)
    sales_orders = parse_json(sales_orders)
    items_in_sales_orders_by_options = {}
    for option in items_in_options:
        items_in_sales_orders = {}
        for item in items_in_options[option]:
            sales_orders_with_item = frappe.db.get_list(
                "Sales Order",
                filters={"name": ["in", sales_orders], "item_code": ["in", [item]]},
                fields=["name"],
                as_list=True,
            )
            items_in_sales_orders[item] = [s[0] for s in sales_orders_with_item]
        items_in_sales_orders_by_options[option] = items_in_sales_orders
    return items_in_sales_orders_by_options


@frappe.whitelist()
def get_unavailable_items_in_cart_by_orders(
    unavailable_items, sales_orders, items_to_sell
):
    unavailable_items = parse_json(unavailable_items)
    sales_orders = parse_json(sales_orders)
    items_to_sell = parse_json(items_to_sell)

    unavailable_items_map = {}
    for d in unavailable_items:
        if d["item_code"] in unavailable_items_map:
            item = unavailable_items_map[d["item_code"]]
            item["required_qty"] += d["required_qty"]
            item["available_qty"] += d["available_qty"]
        else:
            unavailable_items_map[d["item_code"]] = d

    so_items = []
    for d in ("Sales Order Item", "Sales Order Child Item"):
        so_items += frappe.get_all(
            d,
            ["item_code", "item_name", "qty", "parent"],
            {
                "parent": ["in", sales_orders],
                "item_code": ["in", list(unavailable_items_map.keys())],
            },
            order_by="modified desc",
        )

    item_names = frappe.get_all(
        "Item",
        ["item_code", "item_name"],
        {"item_code": ["in", [d["item_code"] for d in items_to_sell]]},
    )

    item_names_map = {}
    for d in item_names:
        item_names_map[d["item_code"]] = d["item_name"]

    for d in items_to_sell:
        d["parent"] = ""
        d["item_name"] = item_names_map[d["item_code"]]

    res = []
    unallocated_items = unavailable_items_map
    for d in so_items + items_to_sell:
        if not d["item_code"] in unallocated_items:
            continue
        unavailable_item = unallocated_items[d["item_code"]]
        unavailable_item["required_qty"] -= d["qty"]
        available_qty = 0
        if unavailable_item["available_qty"] > 0:
            available_qty = unavailable_item["available_qty"]
            if d["qty"] > available_qty:
                unavailable_item["available_qty"] = 0
            else:
                unavailable_item["available_qty"] -= d["qty"]
        if unavailable_item["required_qty"] == 0:
            del unallocated_items[d["item_code"]]
        else:
            unallocated_items[d["item_code"]] = unavailable_item
        res.append(
            {
                "item_code": d["item_code"],
                "item_name": d["item_name"],
                "required_qty": d["qty"],
                "available_qty": available_qty,
                "sales_order": d["parent"],
            }
        )

    return sorted(res, key=lambda d: d["sales_order"])


@frappe.whitelist()
@frappe.validate_and_sanitize_search_inputs
def get_sales_order_query(doctype, txt, searchfield, start, page_len, filters):
    dont_pass = frappe.db.sql(
        "SELECT sales_order_name from `tabPurchase Order Sales Order`"
    )
    dont_pass = [d[0] for d in dont_pass]
    dont_pass += filters["not in"]
    dont_pass_cond = ""
    if len(dont_pass) > 0:
        dont_pass = "(" + ",".join(["'" + d + "'" for d in dont_pass]) + ")"
        dont_pass_cond = f"name NOT IN {dont_pass} AND"

    searchfields = frappe.get_meta("Sales Order").get_search_fields()
    if searchfield:
        searchfields = " or ".join([field + " LIKE %(txt)s" for field in searchfields])

    res = frappe.db.sql(
        """
        SELECT name, customer, total_amount from `tabSales Order`
        WHERE {dont_pass_cond}
        status NOT IN ('Closed', 'Completed', 'Cancelled')
        AND ({scond})
        ORDER BY modified DESC
        LIMIT %(start)s, %(page_len)s
        """.format(
            scond=searchfields, dont_pass_cond=dont_pass_cond
        ),
        {"txt": "%%%s%%" % txt, "start": start, "page_len": page_len},
        as_list=True,
    )

    for d in res:
        d[2] = frappe.format(d[2], "Currency")
    return res


@frappe.whitelist()
def get_purchase_history():
    return IkeaCartUtils().get_purchase_history()


@frappe.whitelist()
def get_purchase_info(purchase_id, use_lite_id):
    utils = IkeaCartUtils()
    purchase_info = None
    try:
        purchase_info = utils.get_purchase_info(purchase_id, use_lite_id=use_lite_id)
    except Exception:
        pass
    return {
        "purchase_info_loaded": True if purchase_info else False,
        "purchase_info": purchase_info,
    }
