from __future__ import annotations

from comfort.entities import Item
from comfort.stock.utils import get_stock_balance
from comfort.transactions import SalesOrder
from comfort.utils import _, get_all, group_by_attr


def _get_purchased_sales_orders_amount() -> int:
    sales_orders = get_all(
        SalesOrder,
        field="(items_cost - paid_amount) as diff",
        filter={
            "payment_status": ("in", ("Unpaid", "Partially Paid", "Overpaid")),
            "delivery_status": ("in", ("Purchased", "To Deliver")),
        },
    )
    return sum(s.diff for s in sales_orders if s.diff > 0)  # type: ignore


def _get_not_purchased_sales_orders_amount():
    sales_orders = get_all(
        SalesOrder,
        field="SUM(paid_amount) as paid_amount",
        filter={
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
    counter = get_stock_balance("Available Actual")
    purchased = get_stock_balance("Available Purchased")
    for item_code in counter:
        if item_code in purchased:
            counter[item_code] += purchased[item_code]

    items_with_rates = get_all(
        Item,
        field=("item_code", "rate"),
        filter={"item_code": ("in", counter.keys())},
    )
    grouped_items = group_by_attr(items_with_rates)

    amount = 0
    for item_code, qty in counter.items():
        amount += grouped_items[item_code][0].rate * qty
    return amount


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
