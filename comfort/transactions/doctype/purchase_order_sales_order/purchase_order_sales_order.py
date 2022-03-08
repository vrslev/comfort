from comfort.utils import TypedDocument


class PurchaseOrderSalesOrder(TypedDocument):
    sales_order_name: str
    customer: str
    total_amount: int
