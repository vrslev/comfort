# GL Entry during Return

**Sales Order**
if not return money:
return items from customer to order new ones
or to cancel after Purchase Return
else:
return money to customer
return items from customer
create new Sales Order
paid money for new Order

**Purchase Order**
if not return money:
return money from supplier
return items to supplier
create new Purchase Order and pay for it
else:
return items
return money to Bank account
always:
return Sales Order as: money + items

if money only:
it is compensation

---

**Purchase Order** — Compensation, Defect or Initiated by supplier
if money: # Compensation
Purchase Compensations -> Cash

if money and items:
if received: # Defect
Inventory -> Cash
else: # Initiated by supplier
Prepaid Inventory -> Cash

if items:
if received: # Defect
Inventory -> Prepaid Inventory
_Create new paid submitted Purchase Order_
else: # ERROR
pass (can't return items cause they are not received yet)

_sales orders_:
if (money and items) or (items):
_Split order_
else:
pass

**Sales Order** — Compensation or Initiated by customer
if money: # Compensation
Cash -> Sales Compensations

if money and items:
if delivered: # Initiated by customer
Cash -> Sales
Cash -> Service
Cost of Goods Sold -> Inventory
else: # ERROR
pass (can't return items cause they are not received yet)

if items: # ERROR

<!-- if delivered: # Initiated by customer
        Cost of Goods Sold -> Inventory
        *Split order*
    else: # ERROR
        pass -->
