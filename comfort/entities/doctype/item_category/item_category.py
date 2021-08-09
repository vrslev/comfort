import re

import frappe
from frappe import _
from frappe.model.document import Document


class ItemCategory(Document):
    url: str

    def validate(self):
        self.validate_url()

    def validate_url(self):
        if self.url:
            if len(re.findall(r"ikea.com/\w+/\w+/cat/-\d+", self.url)) == 0:
                frappe.throw(_("Invalid category URL"))
