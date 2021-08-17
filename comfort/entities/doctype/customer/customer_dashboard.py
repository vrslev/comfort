from typing import Any


def get_data() -> dict[str, Any]:
    return {
        "heatmap": True,
        "fieldname": "customer",
        "transactions": [{"items": ["Sales Order"]}, {"items": ["Purchase Order"]}],
    }
