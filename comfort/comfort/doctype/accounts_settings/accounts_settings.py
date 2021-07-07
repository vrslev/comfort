import frappe
from frappe import clear_cache
from frappe.model.document import Document


class AccountsSettings(Document):
    def on_change(self):
        clear_cache(doctype=self.doctype)


def create_accounts():
    from comfort.comfort.doctype.account.chart_of_accounts.chart_of_accounts import (
        create_charts,
    )

    frappe.local.flags.ignore_root_company_validation = True
    create_charts()


def set_default_accounts(self):
    set_default_field(self, "default_bank_account", "Bank")
    set_default_field(self, "default_cash_account", "Cash")
    set_default_field(self, "default_prepaid_inventory_account", "Prepaid Inventory")
    set_default_field(self, "default_inventory_account", "Inventory")
    set_default_field(self, "default_cost_of_goods_sold_account", "Cost of Goods Sold")
    set_default_field(self, "default_purchase_delivery_account", "Purchase Delivery")
    set_default_field(self, "default_sales_account", "Sales")
    set_default_field(self, "default_delivery_account", "Delivery")
    set_default_field(self, "default_installation_account", "Installation")
    set_default_field(self, "default_prepaid_orders_account", "Prepaid Orders")


def set_default_field(self, default_account_field, account_name):
    frappe.db.set(
        self,
        default_account_field,
        frappe.db.get_value(
            "Account",
            {"account_name": account_name, "is_group": 0},
        ),
    )
