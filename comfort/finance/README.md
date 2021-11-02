# Cash Accounting (with mock invoicing)

https://smallbusiness.chron.com/accounting-policies-invoicing-goods-not-yet-delivered-25664.html

**Assets**
Cash
Bank
Inventory
Prepaid Inventory

**Liabilities**
Prepaid Orders

**Income**
Sales
Service
Delivery
Installation

**Expense**
Service
Delivery
Cost of Goods Sold
*Advertising
*Rent
\*Taxes

## Cycle

- Purchase Order
  paid: Cash -> Prepaid Inventory
  Cash -> Service/Delivery
  received: Prepaid Inventory -> Inventory

- Sales Order
  paid: Prepaid Orders -> Cash
  delivered: Sales -> Prepaid Orders
  Service -> Prepaid Orders
  Inventory -> Cost of Goods Sold

To calculate for Debtors report:
`Prepaid Inventory + Prepaid Orders + Pending Amount of Purchased/To Deliver Sales Orders`

# Cash Accounting (without invoicing)

https://smallbusiness.chron.com/accounting-policies-invoicing-goods-not-yet-delivered-25664.html

- Purchase Order
  paid: Cash -> Prepaid Inventory
  Cash -> Purchase Delivery
  received: Prepaid Inventory -> Inventory

- Sales Order
  paid: Sales -> Cash
  Service -> Cash
  delivered: Inventory -> Cost of Goods Sold

# The Right Way

- Purchase Order

  - paid
    - Cash -> {Prepaid Inventory,Purchase Delivery}
  - received
    - Prepaid Inventory -> Inventory
      (money are gone only for Purchase Delivery; Inventory increased)

- Sales Order

  - paid
    - Prepaid Sales -> Cash
  - delivered
    <!-- Cost of goods sold, margin - service, service -->
    - {Inventory,Sales,Service} -> Prepaid Sales
      (money came only from Sales and Service, Inventory decreased)
