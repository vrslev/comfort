from __future__ import annotations

from copy import deepcopy
from typing import Callable

import pytest

import frappe
from comfort import count_qty, counters_are_same
from comfort.comfort_core.doctype.commission_settings.commission_settings import (
    CommissionSettings,
)
from comfort.entities.doctype.child_item.child_item import ChildItem
from comfort.entities.doctype.item.item import Item
from comfort.finance import create_payment
from comfort.stock.doctype.receipt.receipt import Receipt
from comfort.transactions.doctype.purchase_order.purchase_order import PurchaseOrder
from comfort.transactions.doctype.sales_order.sales_order import (
    SalesOrder,
    get_sales_orders_not_in_purchase_order,
    has_linked_delivery_trip,
    validate_from_available_stock_params,
)
from comfort.transactions.doctype.sales_return.sales_return import SalesReturn
from frappe import ValidationError
from frappe.model.document import Document

#############################
#     SalesOrderMethods     #
#############################


def test_update_items_from_db(sales_order: SalesOrder):
    sales_order.update_items_from_db()

    for i in sales_order.items:
        doc: Item = frappe.get_doc("Item", i.item_code)
        assert i.item_name == doc.item_name
        assert i.rate == doc.rate
        assert i.weight == doc.weight


def test_set_child_items_no_items_set(sales_order: SalesOrder):
    sales_order.items = []
    sales_order.set_child_items()
    assert not sales_order.child_items


def test_set_child_items_items_set(sales_order: SalesOrder, item: Item):
    sales_order.set_child_items()

    item_code_qty_pairs = count_qty(sales_order.child_items).items()
    exp_item_code_qty_pairs = count_qty(item.child_items).items()
    # TODO
    # -        self.child_items = []
    # +        self.child_items = None
    # TODO
    # -            d.qty = d.qty * item_codes_to_qty[d.parent_item_code]
    # +            d.qty = d.qty / item_codes_to_qty[d.parent_item_code]
    # TODO
    # -        base_margin = self.items_cost * self.commission / 100
    # +        base_margin = self.items_cost * self.commission / 101
    for p in exp_item_code_qty_pairs:
        assert p in item_code_qty_pairs


def patch_get_stock_balance(monkeypatch: pytest.MonkeyPatch, result: dict[str, int]):
    import comfort.transactions.doctype.sales_order.sales_order

    mock_get_stock_balance: Callable[[str], dict[str, int]] = lambda stock_type: result
    monkeypatch.setattr(
        comfort.transactions.doctype.sales_order.sales_order,
        "get_stock_balance",
        mock_get_stock_balance,
    )


def test_validate_from_available_stock_not_from_available_stock(
    sales_order: SalesOrder,
):
    sales_order.from_available_stock = None
    sales_order._validate_from_available_stock()


def test_validate_from_available_stock_available_actual_raises(
    monkeypatch: pytest.MonkeyPatch, sales_order: SalesOrder
):
    sales_order.from_available_stock = "Available Actual"
    sales_order.set_child_items()
    mock_stock_counter = count_qty(sales_order._get_items_with_splitted_combinations())
    item_code = list(mock_stock_counter.keys())[0]
    mock_stock_counter[item_code] -= 1
    patch_get_stock_balance(monkeypatch, mock_stock_counter)
    with pytest.raises(
        ValidationError, match=f"Insufficient stock for Item {item_code}"
    ):
        sales_order._validate_from_available_stock()


def test_validate_from_available_stock_available_actual_not_raises(
    monkeypatch: pytest.MonkeyPatch, sales_order: SalesOrder
):
    sales_order.from_available_stock = "Available Actual"
    sales_order.set_child_items()
    mock_stock_counter = count_qty(sales_order._get_items_with_splitted_combinations())
    patch_get_stock_balance(monkeypatch, mock_stock_counter)
    sales_order._validate_from_available_stock()


def test_validate_from_available_stock_available_purchased_raises(
    sales_order: SalesOrder, purchase_order: PurchaseOrder
):
    purchase_order.status = "To Receive"
    purchase_order.db_insert()
    purchase_order.update_children()
    sales_order.from_available_stock = "Available Purchased"
    sales_order.from_purchase_order = purchase_order.name
    sales_order.items = []
    sales_order.child_items = []
    sales_order.append(
        "items",
        {
            "item_code": purchase_order.items_to_sell[0].item_code,
            "qty": purchase_order.items_to_sell[0].qty + 1,
        },
    )
    with pytest.raises(
        ValidationError,
        match=f"Insufficient stock for Item {purchase_order.items_to_sell[0].item_code}",
    ):
        sales_order._validate_from_available_stock()


def test_calculate_item_totals(sales_order: SalesOrder):
    sales_order.update_items_from_db()

    exp_total_quantity, exp_total_weight, exp_items_cost = 0, 0.0, 0
    for i in sales_order.items:
        assert i.amount == i.qty * i.rate
        assert i.total_weight == i.qty * i.weight

        exp_total_quantity += i.qty
        exp_total_weight += i.total_weight
        exp_items_cost += i.amount

    sales_order._calculate_item_totals()

    assert exp_total_quantity == sales_order.total_quantity
    assert exp_total_weight == sales_order.total_weight
    assert exp_items_cost == sales_order.items_cost


def test_calculate_service_amount(sales_order: SalesOrder):
    sales_order._calculate_service_amount()
    service_amount = sum(s.rate for s in sales_order.services)

    assert service_amount == sales_order.service_amount


def test_calculate_commission_no_edit_commission(sales_order: SalesOrder):
    sales_order.items_cost = 5309
    sales_order._calculate_commission()

    assert sales_order.commission == CommissionSettings.get_commission_percentage(
        sales_order.items_cost
    )


def test_calculate_commission_with_edit_commission(sales_order: SalesOrder):
    sales_order.edit_commission = True
    sales_order.commission = 100
    sales_order.items_cost = 21094
    sales_order._calculate_commission()

    assert sales_order.commission == 100


def test_calculate_margin_zero_if_items_cost_is_zero(sales_order: SalesOrder):
    # TODO
    # -        if self.items_cost <= 0:
    # +        if self.items_cost <= 1:
    sales_order.items_cost = 0
    sales_order._calculate_margin()
    assert sales_order.margin == 0


def test_calculate_margin_without_commission(sales_order: SalesOrder):
    sales_order.commission = 0
    sales_order.items_cost = 21214
    sales_order._calculate_margin()
    assert sales_order.margin == -4


def test_calculate_margin_with_commission(sales_order: SalesOrder):
    sales_order.commission = 15
    sales_order.items_cost = 1494
    sales_order._calculate_margin()

    base_margin = sales_order.items_cost * sales_order.commission / 100
    items_cost_rounding_remainder = (
        round(sales_order.items_cost, -1) - sales_order.items_cost
    )
    rounded_margin = round(base_margin, -1) + items_cost_rounding_remainder

    assert rounded_margin == sales_order.margin


def test_calculate_total_amount(sales_order: SalesOrder):
    sales_order.items_cost = 14984
    sales_order.margin = 1496
    sales_order.service_amount = 300
    sales_order.discount = 100
    sales_order._calculate_total_amount()
    exp_total_amount = (
        sales_order.items_cost
        + sales_order.margin
        + sales_order.service_amount
        - sales_order.discount
    )
    assert sales_order.total_amount == exp_total_amount


def test_get_sales_order_items_with_splitted_combinations(sales_order: SalesOrder):
    sales_order.set_child_items()
    items = sales_order._get_items_with_splitted_combinations()
    parents: set[str] = set()
    for child in sales_order.child_items:
        assert child in items
        parents.add(child.parent_item_code)

    for i in sales_order.items:
        if i.item_code in parents:
            assert i not in items
        else:
            assert i in items


def test_create_cancel_sales_return_without_return_before(
    purchase_order: PurchaseOrder, sales_order: SalesOrder
):
    purchase_order.db_insert()
    purchase_order.update_children()
    sales_order.docstatus = 1
    sales_order.db_update()
    sales_order.update_children()
    sales_order.db_set("delivery_status", "Purchased")
    sales_order.docstatus = 2
    sales_order.validate()
    sales_order.load_doc_before_save()
    sales_order._create_cancel_sales_return()

    return_name: str = frappe.get_value(
        "Sales Return", {"sales_order": sales_order.name}
    )
    cancel_return: SalesReturn = frappe.get_doc("Sales Return", return_name)
    assert cancel_return.sales_order == sales_order.name
    assert counters_are_same(
        count_qty(sales_order._get_items_with_splitted_combinations()),
        count_qty(cancel_return.items),
    )


def test_create_cancel_sales_return_with_return_before(
    sales_return: SalesReturn, purchase_order: PurchaseOrder
):
    purchase_order.db_insert()
    purchase_order.update_children()
    sales_order = sales_return._voucher
    prev_counter = count_qty(sales_order._get_items_with_splitted_combinations())
    sales_order.docstatus = 1
    sales_order.db_update()
    sales_order.update_children()
    sales_order.db_set("delivery_status", "Purchased")

    sales_return.insert()
    prev_return_counter = count_qty(sales_return.items)
    sales_return.submit()

    sales_order.docstatus = 2
    sales_order.validate()
    sales_order.load_doc_before_save()
    sales_order._create_cancel_sales_return()

    return_name: str = frappe.get_value(
        "Sales Return", {"sales_order": sales_order.name}
    )
    cancel_return: SalesReturn = frappe.get_doc("Sales Return", return_name)
    new_counter = count_qty(sales_order._get_items_with_splitted_combinations())

    assert cancel_return.sales_order == sales_order.name
    assert counters_are_same(new_counter, count_qty(cancel_return.items))
    assert counters_are_same(prev_counter, new_counter + prev_return_counter)


#############################
#    SalesOrderStatuses     #
#############################


def test_get_paid_amount(sales_order: SalesOrder):
    sales_order.db_insert()
    create_payment(sales_order.doctype, sales_order.name, 300, paid_with_cash=True)
    assert sales_order._get_paid_amount() == 300


def test_get_paid_amount_with_returns(sales_return: SalesReturn):
    sales_order = sales_return._voucher
    sales_order.add_payment(sales_order.total_amount, cash=True)
    sales_return.db_insert()
    sales_return._calculate_returned_paid_amount()
    assert sales_return.returned_paid_amount > 0

    exp_amount = sales_order.total_amount - sales_return.returned_paid_amount
    sales_order.delivery_status = "To Deliver"
    sales_return._make_payment_gl_entries()
    sales_return._make_delivery_gl_entries()
    assert sales_order._get_paid_amount() == exp_amount


@pytest.mark.parametrize(
    "total_amount,paid_amount,exp_per_paid,exp_pending_amount",
    ((10, 10, 100.0, 0), (500, 250, 50.0, 250)),
)
def test_set_paid_and_pending_per_amount(
    sales_order: SalesOrder,
    total_amount: int,
    paid_amount: int,
    exp_per_paid: float,
    exp_pending_amount: int,
):
    sales_order.db_insert()
    create_payment(sales_order.doctype, sales_order.name, paid_amount, True)

    sales_order.total_amount = total_amount
    sales_order._set_paid_and_pending_per_amount()

    assert sales_order.paid_amount == paid_amount
    assert sales_order.per_paid == exp_per_paid
    assert sales_order.pending_amount == exp_pending_amount


def test_set_paid_and_pending_per_amount_with_zero_total_amount(
    sales_order: SalesOrder,
):
    sales_order.total_amount = 0
    sales_order._set_paid_and_pending_per_amount()

    assert sales_order.paid_amount == 0
    assert sales_order.per_paid == 100
    assert sales_order.pending_amount == 0


def test_set_payment_status_with_cancelled_status(sales_order: SalesOrder):
    sales_order.docstatus = 2
    sales_order._set_payment_status()
    assert sales_order.payment_status == ""


@pytest.mark.parametrize(
    "per_paid,expected_status",
    (
        (120, "Overpaid"),
        (100, "Paid"),
        (50, "Partially Paid"),
        (0, "Unpaid"),
        (-20, "Unpaid"),
    ),
)
def test_set_payment_status(
    sales_order: SalesOrder, per_paid: int, expected_status: str
):
    # TODO
    # -        elif self.per_paid > 100:
    # +        elif self.per_paid > 101:
    # TODO:
    # -        elif self.per_paid > 0:
    # +        elif self.per_paid > 1:
    sales_order.per_paid = per_paid
    sales_order._set_payment_status()
    assert sales_order.payment_status == expected_status


def test_set_delivery_status_to_purchase(sales_order: SalesOrder):
    sales_order._set_delivery_status()
    assert sales_order.delivery_status == "To Purchase"


def test_set_delivery_status_purchased(
    sales_order: SalesOrder, purchase_order: PurchaseOrder
):
    for order in purchase_order.sales_orders:
        order.docstatus = 1
    purchase_order.docstatus = 1
    purchase_order.db_update_all()

    sales_order._set_delivery_status()
    assert sales_order.delivery_status == "Purchased"


def test_set_delivery_status_to_deliver(
    sales_order: SalesOrder, purchase_order: PurchaseOrder, receipt_purchase: Receipt
):
    for order in purchase_order.sales_orders:
        order.docstatus = 1
    purchase_order.docstatus = 1
    purchase_order.db_update_all()

    receipt_purchase.docstatus = 1
    receipt_purchase.db_insert()

    sales_order._set_delivery_status()
    assert sales_order.delivery_status == "To Deliver"


def test_set_delivery_status_delivered(sales_order: SalesOrder, receipt_sales: Receipt):
    receipt_sales.docstatus = 1
    receipt_sales.db_insert()
    sales_order._set_delivery_status()
    assert sales_order.delivery_status == "Delivered"


def test_set_delivery_status_with_cancelled_status(sales_order: SalesOrder):
    sales_order.docstatus = 2
    sales_order._set_delivery_status()
    assert sales_order.delivery_status == ""


@pytest.mark.parametrize(
    ("docstatus", "exp_delivery_status"), ((0, "To Purchase"), (1, "To Deliver"))
)
def test_set_delivery_status_from_available_actual_stock(
    sales_order: SalesOrder, docstatus: int, exp_delivery_status: str
):
    sales_order.docstatus = docstatus
    sales_order.from_available_stock = "Available Actual"
    sales_order._set_delivery_status()
    assert sales_order.delivery_status == exp_delivery_status


@pytest.mark.parametrize(
    "docstatus,payment_status,delivery_status,expected_status",
    (
        (0, None, None, "Draft"),
        (1, "Paid", "Delivered", "Completed"),
        (1, None, None, "In Progress"),
        (2, None, None, "Cancelled"),
    ),
)
def test_set_document_status(
    sales_order: SalesOrder,
    docstatus: int,
    payment_status: str,
    delivery_status: str,
    expected_status: str,
):
    # TODO
    # -            if self.payment_status == "Paid" and self.delivery_status == "Delivered":
    # +            if self.payment_status == "Paid" or self.delivery_status == "Delivered":
    sales_order.docstatus = docstatus
    sales_order.payment_status = payment_status
    sales_order.delivery_status = delivery_status
    sales_order._set_document_status()
    assert sales_order.status == expected_status


#############################
#        SalesOrder         #
#############################


def test_sales_order_on_cancel(sales_order: SalesOrder):
    sales_order.update_items_from_db()
    sales_order.calculate()
    sales_order.db_insert()
    sales_order.update_children()
    sales_order.add_payment(100, cash=True)
    sales_order.db_set("delivery_status", "To Deliver")
    sales_order.add_receipt()

    sales_order.on_cancel()
    for doctype in ("Payment", "Receipt"):
        docs: list[Document] = frappe.get_all(
            doctype,
            {"voucher_type": sales_order.doctype, "voucher_no": sales_order.name},
            "docstatus",
        )
        assert all(doc.docstatus == 2 for doc in docs)


def test_add_payment_raises_on_cancelled(sales_order: SalesOrder):
    sales_order.docstatus = 2
    with pytest.raises(
        ValidationError,
        match="Sales Order should be not cancelled to add Payment",
    ):
        sales_order.add_payment(100, True)


def test_add_receipt_raises_on_cancelled(sales_order: SalesOrder):
    sales_order.docstatus = 2
    with pytest.raises(
        ValidationError,
        match="Sales Order should be not cancelled to add Receipt",
    ):
        sales_order.add_receipt()


def test_add_receipt_raises_on_delivered(sales_order: SalesOrder):
    sales_order.delivery_status = "Delivered"
    with pytest.raises(
        ValidationError,
        match='Delivery Status Sales Order should be "To Deliver" to add Receipt',
    ):
        sales_order.add_receipt()


@pytest.mark.parametrize("save", (True, False))
def test_split_combinations(sales_order: SalesOrder, save: bool):
    sales_order.db_insert()
    sales_order.db_update_all()
    sales_order.items = sales_order.items[:1]
    sales_order.items[0].qty = 3
    splitted_combination = deepcopy(sales_order.items[0])

    sales_order.split_combinations([splitted_combination.name], save)

    child_items: list[ChildItem] = frappe.get_all(
        "Child Item",
        fields=("item_code", "qty"),
        filters={"parent": splitted_combination.item_code},
    )
    exp_item_codes_to_qty = count_qty(child_items)
    for i in exp_item_codes_to_qty:
        exp_item_codes_to_qty[i] *= 3
    exp_item_codes_to_qty = exp_item_codes_to_qty.items()

    for i in count_qty(sales_order.items).items():
        assert i in exp_item_codes_to_qty

    # load_doc_before_save is called before save,
    # so this is quite a hack to determine whether document is saved
    doc_was_saved = sales_order.get_doc_before_save() is not None
    assert doc_was_saved if save else not doc_was_saved


# TODO
# @@ -235,7 +235,7 @@
#          self.set_statuses()

#      def before_submit(self):
# -        self.edit_commission = True
# +        self.edit_commission = False
# +        self.edit_commission = None

#      def before_cancel(self):  # pragma: no cover
#          self.set_statuses()


def test_has_linked_delivery_trip_true(sales_order: SalesOrder):
    sales_order.db_insert()
    frappe.get_doc(
        {"doctype": "Delivery Stop", "sales_order": sales_order.name}
    ).db_insert()
    assert has_linked_delivery_trip(sales_order.name)


def test_has_linked_delivery_trip_false(sales_order: SalesOrder):
    sales_order.db_insert()
    assert not has_linked_delivery_trip(sales_order.name)


def test_get_sales_orders_not_in_purchase_order(
    sales_order: SalesOrder, purchase_order: PurchaseOrder
):
    purchase_order.db_insert()
    purchase_order.db_update_all()
    new_name = "random_name"
    new_sales_order: SalesOrder = frappe.get_doc(
        {"doctype": "Sales Order", "name": new_name}
    )
    new_sales_order.db_insert()

    res = get_sales_orders_not_in_purchase_order()
    assert sales_order.name not in res
    assert new_sales_order.name in res


def test_validate_from_available_stock_params_not_from_available_stock(
    sales_order: SalesOrder,
):
    sales_order.from_available_stock = sales_order.from_purchase_order = None
    validate_from_available_stock_params(
        sales_order.from_available_stock, sales_order.from_purchase_order
    )


def test_validate_from_available_stock_params_available_purchased_raises_on_no_from_purchase_order():
    with pytest.raises(
        ValidationError,
        match="If From Available Stock is Available Purchased, From Purchase Order should be set",
    ):
        validate_from_available_stock_params("Available Purchased", None)


@pytest.mark.parametrize("status", ("Draft", "Completed", "Cancelled"))
def test_validate_from_available_stock_params_available_purchased_raises_on_wrong_po_status(
    purchase_order: PurchaseOrder, status: str
):
    purchase_order.status = status
    purchase_order.set_new_name()
    purchase_order.db_insert()
    with pytest.raises(
        ValidationError, match="Status of Purchase Order should be To Receive"
    ):
        validate_from_available_stock_params("Available Purchased", purchase_order.name)


def test_validate_from_available_stock_params_available_purchased_raises_on_no_items_to_sell(
    purchase_order: PurchaseOrder,
):
    purchase_order.status = "To Receive"
    purchase_order.items_to_sell = []
    purchase_order.db_insert()
    purchase_order.update_children()
    with pytest.raises(ValidationError, match="No Items To Sell in Purchase Order"):
        validate_from_available_stock_params("Available Purchased", purchase_order.name)


def test_validate_from_available_stock_params_available_purchased_passes(
    purchase_order: PurchaseOrder,
):
    purchase_order.status = "To Receive"
    purchase_order.db_insert()
    purchase_order.update_children()
    validate_from_available_stock_params("Available Purchased", purchase_order.name)


def test_validate_from_available_stock_params_available_actual_raises_on_no_stock_balance():
    with pytest.raises(ValidationError, match="No Items in Available Actual stock"):
        validate_from_available_stock_params("Available Actual", None)


def test_validate_from_available_stock_params_available_actual_passes(
    monkeypatch: pytest.MonkeyPatch,
):
    patch_get_stock_balance(monkeypatch, {"10014030": 1})
    validate_from_available_stock_params("Available Actual", None)
