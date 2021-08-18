Sales Order has several stages. To determine if I need real transactional ERP, need to know cons and pros.

1. Sales Order Creation
   Before items in Sales Order are purchased, nothing destructive happens.

2. Payment
   More likely there's advance payment. So, GL Entries (IN) are created to capture it.

3. Purchasing
   Items are purchased. So, Bins are updated.
   Sales Orders are submitted.
   GL Entries are created (OUT)

4. Purchase Receipt
   Items are accepted. So, Bins are updated.

5. Additional services
   Sales Orders are modified. GL Entries are created.

6. Sales Orders Completion
   Bin is updated.

7. Cancellation
   Some stuff could be returned.

---

It is probably bad thing that items in Purchase Order are associated with Sales Orders.
This way, nothing can be changed not descructively.
But, it makes process so much easier for user...

---

What if customer wants to return items?

Need to modify:

- Sales Order
- Purchase Order
- Bin
- and add new GL Entries

Problem is, that every particular Transaction contains whole bunch of stuff.
But, if you would split all of these in partitions than it lacks of usability

---

Entities. They’re describing abstractions (account) or real objects (customer, item).
Events. Change of goods: we buy item from supplier, make services and give it to customer.
To summarize events that happen to and with entities, we have transactions (purchase order, sales order, return).

First problem is that useful data in transactions is mixed with automatically generated stuff.

Second—it is hard to safely modify something in order.

So, process should be event driven.
For example, customer cancels order after payment and when items already purchased, any operations shouldn’t be undoable. I should be able to change something when I changed my mind.

---

I should create system where every operation can be reversed.

**Example: Purchase**

Stock Entry is created to describe that we ordered some items. And not just ordered but some are available for Sales and some are booked.
When we want to reverse this event back, just cancel this Stock Entry. But... Than timeline is messed up: we know when we cancelled this operation—when it was initialized? But... Is it okay to move stock here-and-there?

Also, what if supplier cancelled Purchase Order without any reason and returned money back?
Should we _cancel_ GL Entries linked to this Purchase or _create cancelled_ GL Entries to show that money was there and now they're here?

Probably, should _cancel_ and not _create cancelled_ documents.

---

_I should get rid of Bin doctype in favor of Stock Entries. In ERPNext it only caches values taken from Stock Entries. I don't want that._

Alright. In our business there's just a few destructive _events_. I want them to be reversible.

- Sales Order Payment
- Purchase Order Submission
- Purchase Order Receipt
- Sales Order Update
- Sales Order Receipt
- Return

**Sales Order Payment**
To guarantee cancellability, it should have Payment Entry

- Create Payment Entry with simple prompt
- If something goes wrong, cancel it

It should be backwards: I should be able to pay back. But it used only for compensations and returns or if something is not available.

**Sales Order Receipt**
To guarantee cancellability, it should have Receipt Entry
Receipt Entry shouldn't have any fields. Just "received".

- Create Receipt Entry with one button
- If something goes wrong, cancel it

**Sales Order Update**
Since it is transaction and update requires real change in it, what should I do?
Maybe, make good timeline?
Kinds of changes there could be:

- discount
- commission
  Discount changes when client is not satisfied or something. It's fine if this changes.
  Commission is being changed manually when items are changed and user decided to do it. It is fine if commission changed by user.

Items change when Return is created (whole other case). If user changes items directly in Sales Order it means that... Actually, I can't think of cases that Return wouldn't cover.

- Change discount or commission directly in Sales Order
- To cancel, just change it back.

**Purchase Order Submission**
Automatically:

- Submit Sales Orders.
- Create GL Entries for this Purchase Order.
- Create Stock Entries.
  On Purchase Order cancellation:
- Unsubmit Sales Orders (is this possible?)
- Cancel GL Entries associated with this Purchase Order.
- Cancel Stock Entries.

**Purchase Order Receipt**

- Create Receipt Entry with simple button.
  - On Receipt Entry creation add Stock Entries.
- To cancel, cancel Receipt Entry.

---

# Payment

## Sales Order

In any time — create new Payment. To cancel, just cancel Payment.

## Purchase Order

On submission create Payment. Shouldn't be able to cancel it manually. Cancel on Purchase Order cancellation.

---
