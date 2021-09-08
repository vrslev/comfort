def get_data():
    return {
        "fieldname": "voucher_no",
        "non_standard_fieldnames": {
            "Checkout": "purchase_order",
            "Purchase Return": "purchase_order",
        },
        "transactions": [
            {"items": ["Payment", "Checkout", "Receipt"]},
            {"items": ["Purchase Return"]},
        ],
    }
