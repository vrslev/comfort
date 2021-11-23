from __future__ import annotations

from comfort import _, get_all
from comfort.transactions.doctype.purchase_order.purchase_order import PurchaseOrder
from comfort.transactions.doctype.purchase_order_item_to_sell.purchase_order_item_to_sell import (
    PurchaseOrderItemToSell,
)
from comfort.transactions.doctype.sales_order.sales_order import SalesOrder


def _get_purchased_sales_orders_amount() -> int:
    sales_orders = get_all(
        SalesOrder,
        fields="(items_cost - paid_amount) as diff",
        filters={
            "payment_status": ("in", ("Unpaid", "Partially Paid", "Overpaid")),
            "delivery_status": ("in", ("Purchased", "To Deliver")),
        },
    )
    return sum(s.diff for s in sales_orders if s.diff > 0)  # type: ignore


def _get_not_purchased_sales_orders_amount():
    sales_orders = get_all(
        SalesOrder,
        fields="SUM(paid_amount) as paid_amount",
        filters={
            "payment_status": ("in", ("Partially Paid", "Paid", "Overpaid")),
            "delivery_status": (
                "in",
                (
                    "",  # cancelled
                    "To Purchase",
                ),
            ),
        },
    )
    return sales_orders[0].paid_amount or 0


def _get_items_to_sell_amount():
    purchase_orders = get_all(PurchaseOrder, filters={"docstatus": 1})
    items = get_all(
        PurchaseOrderItemToSell,
        fields=("SUM(amount) as amount"),
        filters={"parent": ("in", (o.name for o in purchase_orders))},
    )
    return items[0].amount or 0


def _get_report_summary():
    sales_orders_amount = _get_purchased_sales_orders_amount()
    items_to_sell_amount = _get_items_to_sell_amount()
    not_purchased_sales_orders_amount = _get_not_purchased_sales_orders_amount()
    total_amount = (
        sales_orders_amount - not_purchased_sales_orders_amount + items_to_sell_amount
    )
    return [
        {
            "value": sales_orders_amount,
            "label": _("Purchased Sales Orders"),
            "datatype": "Currency",
        },
        {"type": "separator", "value": "-"},
        {
            "value": not_purchased_sales_orders_amount,
            "label": _("Not Purchased Sales Orders"),
            "datatype": "Currency",
        },
        {"type": "separator", "value": "+"},
        {
            "value": items_to_sell_amount,
            "label": _("Items to Sell"),
            "datatype": "Currency",
        },
        {"type": "separator", "value": "="},
        {
            "value": total_amount,
            "indicator": "Green" if total_amount > 0 else "Red",
            "label": _("Total"),
            "datatype": "Currency",
        },
    ]


def execute(filters: dict[str, str]):
    return (), (), None, None, _get_report_summary()
