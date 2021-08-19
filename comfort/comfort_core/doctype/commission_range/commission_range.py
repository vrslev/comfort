from frappe.model.document import Document


class CommissionRange(Document):
    percentage: int
    from_amount: int
    to_amount: int
