from __future__ import annotations

from collections import defaultdict

import frappe
from comfort import ValidationError, count_qty, group_by_attr
from comfort.entities.doctype.child_item.child_item import ChildItem
from comfort.entities.doctype.item.item import Item
from comfort.finance import cancel_gl_entries_for, create_gl_entry, get_account
from comfort.stock import cancel_stock_entries_for, create_stock_entry
from comfort.transactions import (
    AnyChildItem,
    Return,
    delete_empty_items,
    merge_same_items,
)
from frappe import _

from ..purchase_order.purchase_order import PurchaseOrder
from ..purchase_order_item_to_sell.purchase_order_item_to_sell import (
    PurchaseOrderItemToSell,
)
from ..purchase_order_sales_order.purchase_order_sales_order import (
    PurchaseOrderSalesOrder,
)
from ..purchase_return_item.purchase_return_item import PurchaseReturnItem
from ..sales_order.sales_order import SalesOrder
from ..sales_return.sales_return import SalesReturn


class PurchaseReturn(Return):
    purchase_order: str
    returned_paid_amount: int
    items: list[PurchaseReturnItem]

    __voucher: PurchaseOrder | None = None

    @property
    def _voucher(self) -> PurchaseOrder:
        if not self.__voucher:
            self.__voucher: PurchaseOrder = frappe.get_doc(
                "Purchase Order", self.purchase_order
            )
        return self.__voucher

    def _calculate_returned_paid_amount(self):
        self.returned_paid_amount = sum(item.qty * item.rate for item in self.items)

    def _validate_voucher_statuses(self):
        if self._voucher.docstatus != 1:
            raise ValidationError(_("Purchase Order should be submitted"))

        if self._voucher.status not in ("To Receive", "Completed"):
            raise ValidationError(_("Status should be To Receive or Completed"))

    def _get_all_items(self):
        items: list[AnyChildItem] = []
        items += self._voucher._get_items_to_sell(True)
        # Using this way instead of _get_items_in_sales_orders(True)
        # to have `parent` and `doctype` fields in these items
        for sales_order in self._voucher.sales_orders:
            doc: SalesOrder = frappe.get_doc(
                "Sales Order", sales_order.sales_order_name
            )
            items += doc._get_items_with_splitted_combinations()
        return items

    def _allocate_items(self):
        orders_to_items: defaultdict[
            str | None, list[dict[str, str | int]]
        ] = defaultdict(list)

        def append_item(item: AnyChildItem):
            item_dict: dict[str, str | int] = {
                "item_code": item.item_code,
                "item_name": item.item_name,
                "qty": item.qty,
                "rate": item.rate,
            }
            if item.get("doctype") in ("Sales Order Item", "Sales Order Child Item"):
                orders_to_items[item.parent].append(item_dict)
            else:
                orders_to_items[None].append(item_dict)

        all_items = self._get_all_items()
        self._add_missing_fields_to_items(all_items)
        grouped_items = group_by_attr(all_items)
        for item_code, qty in count_qty(self.items).items():
            for item in grouped_items[item_code]:
                if item.qty >= qty:
                    item.qty = qty
                    append_item(item)
                    break
                else:
                    append_item(item)
                    qty -= item.qty

        return orders_to_items

    def _make_sales_returns(
        self, orders_to_items: defaultdict[str | None, list[AnyChildItem]]
    ):
        to_remove: list[PurchaseOrderSalesOrder] = []
        for order_name, items in orders_to_items.items():
            if order_name is None:
                continue
            doc: SalesReturn = frappe.new_doc("Sales Return")
            doc.sales_order = order_name
            doc.from_purchase_return = self.name
            doc.extend("items", items)
            doc.insert()
            doc.submit()

            if doc._voucher.docstatus == 2:
                for order in self._voucher.sales_orders:
                    if order.sales_order_name == doc._voucher.name:
                        to_remove.append(order)

        for order in to_remove:
            self._voucher.sales_orders.remove(order)

    def _add_missing_field_to_voucher_items_to_sell(
        self, items: list[PurchaseOrderItemToSell | ChildItem]
    ):
        def include(item: PurchaseOrderItemToSell | ChildItem):
            if (
                not item.get("rate")
                or not item.get("weight")
                or not item.get("item_name")
                or not item.get("amount")
            ):
                return True

        items_with_missing_fields: list[Item] = frappe.get_all(
            "Item",
            fields=("item_code", "item_name", "rate", "weight"),
            filters={"item_code": ("in", (i.item_code for i in items if include(i)))},
        )
        grouped_items = group_by_attr(items_with_missing_fields)
        for item in items:
            if item.item_code in grouped_items:
                grouped_item = grouped_items[item.item_code][0]
                item.item_name = grouped_item.item_name
                item.rate = grouped_item.rate
                item.weight = grouped_item.weight
            item.amount = item.qty * item.rate

    def _split_combinations_in_voucher(self):
        items = merge_same_items(self._voucher._get_items_to_sell(True))
        self._add_missing_field_to_voucher_items_to_sell(items)
        self._voucher.items_to_sell = []
        self._voucher.extend("items_to_sell", items)

    def _modify_voucher(
        self, orders_to_items: defaultdict[str | None, list[AnyChildItem]]
    ):
        self._split_combinations_in_voucher()

        qty_counter = count_qty(frappe._dict(i) for i in orders_to_items[None])
        for item in self._voucher.items_to_sell:
            if item.item_code in qty_counter:
                item.qty -= qty_counter[item.item_code]
                del qty_counter[item.item_code]

        delete_empty_items(self._voucher, "items_to_sell")
        self._voucher.items_to_sell = merge_same_items(self._voucher.items_to_sell)
        # NOTE: Never use `update_items_to_sell_from_db`
        self._voucher.update_sales_orders_from_db()
        self._voucher.calculate()
        self._voucher.db_update()
        self._voucher.update_children()

    def _make_gl_entries(self):
        """Return `returned_paid_amount` to "Cash" or "Bank"."""
        inventory_account = {
            "To Receive": "prepaid_inventory",
            "Completed": "inventory",
        }[self._voucher.status]

        amt = self.returned_paid_amount
        create_gl_entry(self.doctype, self.name, get_account(inventory_account), 0, amt)
        create_gl_entry(self.doctype, self.name, get_account("bank"), amt, 0)

    def _make_stock_entries(self):
        """Return items to supplier.

        Since Sales Returns make Stock Entries (Reserved -> Available), making only (Available -> None)
        """
        stock_type = {
            "To Receive": "Available Purchased",
            "Completed": "Available Actual",
        }[self._voucher.status]
        create_stock_entry(
            self.doctype, self.name, stock_type, self.items, reverse_qty=True
        )

    def before_submit(self):  # pragma: no cover
        orders_to_items = self._allocate_items()
        self._make_sales_returns(orders_to_items)
        self._modify_voucher(orders_to_items)
        self._make_gl_entries()
        self._make_stock_entries()

    def on_cancel(self):
        if self._voucher.status != "To Receive":
            raise ValidationError(
                _(
                    "Allowed to cancel Purchase Return only if status of Order is To Receive"
                )
            )

        sales_returns: list[SalesReturn] = frappe.get_all(
            "Sales Return", {"from_purchase_return": self.name}
        )
        for return_ in sales_returns:
            doc: SalesReturn = frappe.get_doc("Sales Return", return_.name)
            doc.flags.from_purchase_return = True
            doc.cancel()

        cancel_gl_entries_for(self.doctype, self.name)
        cancel_stock_entries_for(self.doctype, self.name)
