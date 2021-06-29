from frappe import _


def get_data():
    return {
        "heatmap": True,
        "fieldname": "customer",
        "transactions": [{"items": ["Sales Order"]}, {"items": ["Purchase Order"]}],
    }
