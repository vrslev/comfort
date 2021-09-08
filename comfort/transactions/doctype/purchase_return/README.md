# Returns

## Sales Return

Accepted delivery statuses: Purchased, To Deliver, Delivered

- Modify Sales Order

GL Entry: Cash/Bank -> Sales (only if overpaid)

### Purchased

Stock Entry: Reserved Purchased -> Available Purchased

### To Deliver

Stock Entry: Reserved Actual -> Available Actual

### Delivered

GL Entry: Cost of Goods Sold -> Inventory

Stock Entry: Reserved Actual -> Available Actual

## Purchase Return

Accepted statuses: To Receive, Completed

- Make Sales Returns
- Modify items to sell

### To Receive

GL Entry: Prepaid Inventory -> Cash/Bank

Stock Entry: Available Purchased -> None

### Completed

GL Entry: Inventory -> Cash/Bank

Stock Entry: Available Actual -> None

## Links

If To Receive then Purchased
If Completed then To Deliver or Delivered
