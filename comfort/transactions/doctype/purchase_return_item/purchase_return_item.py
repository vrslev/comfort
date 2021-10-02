from comfort import TypedDocument


class PurchaseReturnItem(TypedDocument):
    item_code: str
    item_name: str
    qty: int
    rate: int
    amount: int
