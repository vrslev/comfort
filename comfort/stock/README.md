# Purchase Order

- To Receive (purchased)
  -> available_purchased and reserved_purchased

- Completed
  available_purchased and reserved_purchased -> available_actual and reserved_actual

- Purchase Return
  available_purchased or available_actual ->

- Cancelled
  Allowed only if status is To Receive
  Cancel all linked docs except Sales Orders—this will do.

# Sales Order

- Delivered
  reserved_actual ->

- Sales Return
  reserved_purchased or reserved_actual -> available_purchased or available_actual
  if all items: create nothing

- Cancelled
  create Sales Return for remaining items
  - Cancel Receipt
    -> reserved_actual
