def get_data():
    return {
        "fieldname": "voucher_no",
        "non_standard_fieldnames": {"Purchase Order": "sales_order_name"},
        "transactions": [
            {"items": ["Payment", "Receipt"]},
        ],
    }
