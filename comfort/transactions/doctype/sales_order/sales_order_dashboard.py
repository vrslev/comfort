def get_data():
    return {
        "fieldname": "voucher_no",
        "non_standard_fieldnames": {
            "Purchase Order": "sales_order_name",
            "Delivery Trip": "sales_order",
        },
        "transactions": [
            {"items": ["Payment"]},
            {"items": ["Purchase Order"]},
            {"items": ["Delivery Trip", "Receipt"]},
        ],
    }
