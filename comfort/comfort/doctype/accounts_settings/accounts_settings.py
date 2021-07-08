from frappe import clear_cache
from frappe.model.document import Document


class AccountsSettings(Document):
    def on_change(self):
        clear_cache(doctype=self.doctype)
