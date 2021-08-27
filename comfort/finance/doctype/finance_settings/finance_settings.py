from frappe.model.document import Document


class FinanceSettings(Document):
    def on_change(self):
        self.clear_cache()
