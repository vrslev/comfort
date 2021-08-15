from frappe.model.document import Document


class GLEntry(Document):
    account: str
    credit_amount: int
    debit_amount: int
