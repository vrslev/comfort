from typing import Any

from frappe import _


def get_data() -> dict[str, Any]:
    return {
        "heatmap": True,
        "fieldname": "customer",
        "transactions": [{"items": ["Sales Order"]}, {"items": ["Purchase Order"]}],
    }
