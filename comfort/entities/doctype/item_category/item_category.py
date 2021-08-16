import re

from comfort import ValidationError
from frappe import _
from frappe.model.document import Document


class ItemCategory(Document):
    url: str

    def validate(self):  # pragma: no cover
        self.validate_url()

    def validate_url(self):
        if self.url:
            if len(re.findall(r"ikea.com/\w+/\w+/cat/-\d+", self.url)) == 0:
                raise ValidationError(_("Invalid category URL"))
