STOCK CYCLE

Purchased SUPPLIER -> available_purchased
-> reserved_purchased
Received reserved_purchased -> reserved_actual
available_purchased -> available_actual

- Client ordered available_actual -> reserved_actual
  something from
  Actual Stock

  Delivered reserved_actual -> CUSTOMER

? Client ordered something while items not received yet
Instead of Select field `source`, the best way to implement injecting Sales Orders
into Purchase Order would be button inside this Purchase Order with prompt to
choose items and create Sales Order.
This way no double links would be created, and it is much clearer.

    When Purchase Order completed,
    it's time to forget about it. But when it is pending, the hard way should be
    chosen: move items to sell to new Sales Order

    The only problem is that system can't force user to submit new Sales Order.

    So, there should be `from_actual_stock` check.

    1. If new Sales Order (will purchase specially for customer): nothing new
    2. If from Items To Sell:
        - if not received yet: add this Sales Order from Purchase Order
            (using button in Items To Sell grid)
        - else, if Purchase Order received, just create Sales Order normal way.

    To make this work:
    - [ ] Change `source` Select field to `from_actual_stock` check
    - [ ] Change functions related to this fields
    - [ ] Add mechanism to create Sales Order from Purchase Order that is
            not received yet

? Cancelled

What if someone bought something while items not received yet?
Sales Order added this way should appear in Purchase order
