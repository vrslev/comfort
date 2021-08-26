def get_data():
    return {
        "fieldname": "voucher_no",
        "non_standard_fieldnames": {"Checkout": "purchase_order"},
        "transactions": [
            {"items": ["Payment", "Checkout", "Receipt"]},
        ],
    }
