# from collections import Counter

# from comfort.stock import get_stock_balance
# from comfort.transactions.doctype.purchase_return.purchase_return import PurchaseReturn
# from comfort.transactions.doctype.sales_order.sales_order import SalesOrder

# # def test_purchase_return_allocate_items(purchase_return: PurchaseReturn):
# #     purchase_return._allocate_items()


# # def test_create_sales_returns(purchase_return: PurchaseReturn, sales_order: SalesOrder):
# #     sales_order.reload()
# #     sales_order.docstatus = 1
# #     sales_order.delivery_status = "Purchased"
# #     sales_order.db_update_all()
# #     purchase_return._make_sales_returns()


# # def test_purchase_return_make_stock_entries(purchase_return: PurchaseReturn):
# #     purchase_return._voucher.status = "To Receive"
# #     items = purchase_return._get_all_items()
# #     purchase_return._add_missing_fields_to_items(items)
# #     purchase_return._make_stock_entries(items)


# # def test_purchase_return_before_submit(
# #     purchase_return: PurchaseReturn, sales_order: SalesOrder
# # ):
# #     purchase_return._voucher.status = "To Receive"
# #     purchase_return._voucher.total_amount = 1000
# #     purchase_return._voucher.submit()
# #     sales_order.reload()
# #     sales_order.docstatus = 1
# #     sales_order.delivery_status = "Purchased"
# #     sales_order.db_update_all()
# #     stock_balance_before = [
# #         Counter(get_stock_balance(s))
# #         for s in (
# #             "Reserved Actual",
# #             "Available Actual",
# #             "Reserved Purchased",
# #             "Available Purchased",
# #         )
# #     ]
# #     purchase_return.before_submit()
# #     stock_balance_after = [
# #         Counter(get_stock_balance(s))
# #         for s in (
# #             "Reserved Actual",
# #             "Available Actual",
# #             "Reserved Purchased",
# #             "Available Purchased",
# #         )
# #     ]
# #     # Reserved Purchased: 10366598(-1)
# #     for before, after in zip(stock_balance_before, stock_balance_after):
# #         print(before)
# #         print(after)
# #     assert False
