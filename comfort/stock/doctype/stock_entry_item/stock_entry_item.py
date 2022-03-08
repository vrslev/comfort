from comfort.utils import TypedDocument


class StockEntryItem(TypedDocument):
    item_code: str
    qty: int
