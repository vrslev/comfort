from typing import TypeVar, Union

from comfort.entities.doctype.child_item.child_item import ChildItem
from comfort.transactions.doctype.purchase_order_item_to_sell.purchase_order_item_to_sell import (
    PurchaseOrderItemToSell,
)
from comfort.transactions.doctype.sales_order_child_item.sales_order_child_item import (
    SalesOrderChildItem,
)
from comfort.transactions.doctype.sales_order_item.sales_order_item import (
    SalesOrderItem,
)
from comfort.utils import count_qty, group_by_attr

AnyChildItem = Union[
    SalesOrderItem, SalesOrderChildItem, ChildItem, PurchaseOrderItemToSell
]


def delete_empty_items(self: object, items_field: str) -> None:
    """Delete items that have zero quantity."""
    items: list[AnyChildItem] = getattr(self, items_field)
    new_items: list[AnyChildItem] = []
    for item in items:
        if item.qty != 0:
            new_items.append(item)
    setattr(self, items_field, new_items)


_T = TypeVar("_T", bound=AnyChildItem)


def merge_same_items(items: list[_T]) -> list[_T]:
    """Merge items that have same Item Code."""
    counter = count_qty(items)
    new_items: list[_T] = []
    for item_code, cur_items in group_by_attr(items).items():
        cur_items[0].qty = counter[item_code]
        new_items.append(cur_items[0])
    return new_items
