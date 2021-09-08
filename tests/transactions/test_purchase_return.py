from comfort.transactions.doctype.purchase_order.purchase_order import PurchaseOrder
from comfort.transactions.doctype.purchase_return.purchase_return import PurchaseReturn


def test_purchase_return_voucher_property(purchase_return: PurchaseReturn):
    assert type(purchase_return._voucher) == PurchaseOrder
    assert purchase_return._voucher.name == purchase_return.purchase_order


def test_purchase_return_calculate_returned_paid_amount(
    purchase_return: PurchaseReturn,
):
    purchase_return._calculate_returned_paid_amount()
    raise Exception(purchase_return.returned_paid_amount)
