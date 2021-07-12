import frappe


def test():
    for d in (
        # 'Account',
        "GL Entry",
        "Sales Order",
        "Sales Order Child Item",
        "Sales Order Item",
        "Purchase Order",
        "Purchase Order Item To Sell",
        "Purchase Order Sales Order",
        "Return",
        "Return Item",
    ):
        print(frappe.db.sql(f"""DELETE FROM `tab{d}`"""))
        frappe.db.commit()
