from comfort.utils import TypedDocument


class CommissionRange(TypedDocument):
    percentage: int
    from_amount: int
    to_amount: int
