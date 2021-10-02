from comfort import TypedDocument


class SalesReturnItem(TypedDocument):
    item_code: str
    item_name: str
    qty: int
    rate: int
    amount: int
