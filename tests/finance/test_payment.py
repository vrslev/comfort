import pytest

import frappe
from comfort.finance.doctype.payment.payment import Payment
from comfort.transactions.doctype.sales_order.sales_order import SalesOrder


@pytest.fixture
def payment(sales_order: SalesOrder) -> Payment:
    sales_order.db_insert()
    return frappe.get_doc(
        {
            "name": "ebd35a9cc9",
            "docstatus": 0,
            "voucher_type": "Sales Order",
            "voucher_no": "SO-2021-0001",
            "amount": 5000,
            "paid_with_cash": 0,
            "doctype": "Payment",
        }
    )


# #############################
# #     SalesOrderFinance     #
# #############################


# def get_gl_entries(doc: SalesOrder) -> list[GLEntry]:
#     return frappe.get_all(
#         "GL Entry",
#         fields=["account", "debit", "credit"],
#         filters={"voucher_type": doc.doctype, "voucher_no": doc.name},
#     )


# def test_get_amounts_for_invoice_gl_entries(sales_order: SalesOrder):
#     sales_order.total_amount = 10000
#     sales_order.service_amount = 800
#     amounts = sales_order._get_amounts_for_invoice_gl_entries()

#     assert amounts["sales_amount"] == 9200
#     assert amounts["delivery_amount"] == 300
#     assert amounts["installation_amount"] == 500


# @pytest.mark.parametrize(
#     "paid_amount,exp_sales_amount,exp_delivery_amount,exp_installation_amount",
#     (
#         (500, 500, 0, 0),
#         (5000, 5000, 0, 0),
#         (5200, 5000, 200, 0),
#         (5400, 5000, 300, 100),
#         (5800, 5000, 300, 500),
#         (5900, 5100, 300, 500),
#     ),
# )
# def test_make_categories_invoice_gl_entries(
#     sales_order: SalesOrder,
#     paid_amount: int,
#     exp_sales_amount: int,
#     exp_delivery_amount: int,
#     exp_installation_amount: int,
# ):
#     sales_order.total_amount = 5800
#     sales_order.service_amount = 800
#     sales_order.db_insert()

#     sales_order._make_categories_invoice_gl_entries(
#         paid_amount, **sales_order._get_amounts_for_invoice_gl_entries()
#     )

#     amounts = {"sales": 0, "delivery": 0, "installation": 0}

#     for entry in get_gl_entries(sales_order):
#         for account_name in amounts:
#             if get_account(account_name) == entry.account:
#                 amounts[account_name] += entry.credit

#     assert amounts["sales"] == exp_sales_amount
#     assert amounts["delivery"] == exp_delivery_amount
#     assert amounts["installation"] == exp_installation_amount


# def test_make_categories_invoice_gl_entries_skips_on_zero_fund_amount(
#     sales_order: SalesOrder,
# ):
#     sales_order.db_insert()
#     sales_order._make_categories_invoice_gl_entries(500, 0, 300, 200)
#     accounts = [entry.account for entry in get_gl_entries(sales_order)]
#     assert get_account("sales") not in accounts


# @pytest.mark.parametrize(
#     "paid_with_cash,expected_account", ((True, "cash"), (False, "bank"))
# )
# def test_make_income_invoice_gl_entry(
#     sales_order: SalesOrder, paid_with_cash: bool, expected_account: str
# ):
#     sales_order.db_insert()
#     sales_order._make_income_invoice_gl_entry(5000, paid_with_cash)

#     amount = 0
#     for entry in get_gl_entries(sales_order):
#         assert entry.account == get_account(expected_account)
#         amount += entry.debit
#     assert amount == 5000


# def test_make_invoice_gl_entries_raises_on_zero_paid_amount(sales_order: SalesOrder):
#     with pytest.raises(ValidationError, match="Paid Amount should be more that zero"):
#         sales_order.make_invoice_gl_entries(0, True)


# def test_make_invoice_gl_entries_raises_on_zero_total_amount(sales_order: SalesOrder):
#     sales_order.total_amount = 0
#     with pytest.raises(ValidationError, match="Total Amount should be more that zero"):
#         sales_order.make_invoice_gl_entries(100, True)


# def test_make_delivery_gl_entries(sales_order: SalesOrder):
#     items_cost = 5000

#     sales_order.items_cost = items_cost
#     sales_order.delivery_status = "Delivered"
#     sales_order.db_insert()
#     sales_order.make_delivery_gl_entries()

#     for entry in get_gl_entries(sales_order):
#         if get_account("inventory") == entry.account:
#             assert entry.credit == items_cost
#         elif get_account("cost_of_goods_sold") == entry.account:
#             assert entry.debit == items_cost


# def test_make_delivery_gl_entries_raises_on_wrong_delivery_status(
#     sales_order: SalesOrder,
# ):
#     sales_order.delivery_status = "To Deliver"
#     sales_order.db_insert()
#     with pytest.raises(
#         ValidationError, match='Cannot make GL Entries when status is not "Delivered"'
#     ):
#         sales_order.make_delivery_gl_entries()
