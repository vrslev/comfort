from __future__ import annotations

import re

from comfort import ValidationError
from frappe import _
from frappe.model.document import Document


class ItemCategory(Document):
    item_category_name: str
    url: str | None

    def validate(self):  # pragma: no cover
        self.validate_url()

    def validate_url(self):
        if self.url:
            if len(re.findall(r"ikea.com/\w+/\w+/cat/-\d+", self.url)) == 0:
                raise ValidationError(_("Invalid category URL"))
