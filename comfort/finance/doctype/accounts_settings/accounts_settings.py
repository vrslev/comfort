from frappe.model.document import Document


class AccountsSettings(Document):
    def on_change(self):
        self.clear_cache()
