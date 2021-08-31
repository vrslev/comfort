def get_data():
    return {
        "fieldname": "customer",
        "non_standard_fieldnames": {"Purchase Order": "customer"},
        "transactions": [{"items": ["Sales Order"]}, {"items": ["Purchase Order"]}],
    }
