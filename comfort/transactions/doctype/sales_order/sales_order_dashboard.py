def get_data():
    return {
        "fieldname": "voucher_no",
        "non_standard_fieldnames": {
            "Purchase Order": "sales_order_name",
            "Delivery Trip": "sales_order",
            "Sales Return": "sales_order",
        },
        "transactions": [
            {"items": ["Payment", "Compensation"]},
            {
                "items": [
                    "Purchase Order",
                    "Sales Return",
                ]
            },
            {"items": ["Delivery Trip", "Receipt"]},
        ],
    }
