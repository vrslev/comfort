from comfort import TypedDocument


class StockEntryItem(TypedDocument):
    item_code: str
    qty: int
