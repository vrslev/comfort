import frappe


def create_accounts():
    from comfort.finance.chart_of_accounts import create_charts

    frappe.local.flags.ignore_root_company_validation = True
    create_charts()

    doc = frappe.get_single("Accounts Settings")
    doc.default_bank_account = "Bank"
    doc.default_cash_account = "Cash"
    doc.default_prepaid_inventory_account = "Prepaid Inventory"
    doc.default_inventory_account = "Inventory"
    doc.default_cost_of_goods_sold_account = "Cost of Goods Sold"
    doc.default_purchase_delivery_account = "Purchase Delivery"
    doc.default_sales_account = "Sales"
    doc.default_delivery_account = "Delivery"
    doc.default_installation_account = "Installation"
    doc.default_sales_compensations_account = "Sales Compensations"
    doc.default_purchase_compensations_account = "Purchase Compensations"
    doc.save()


def after_install():
    create_accounts()
