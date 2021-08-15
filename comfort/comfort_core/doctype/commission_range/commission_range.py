from frappe.model.document import Document


class CommissionRange(Document):
    percentage: int
    from_amount: float
    to_amount: float
