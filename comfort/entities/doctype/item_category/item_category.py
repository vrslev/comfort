from __future__ import annotations

import re

from comfort import TypedDocument, ValidationError, _


class ItemCategory(TypedDocument):
    category_name: str
    url: str | None

    def validate(self):
        if not self.url:
            return
        if len(re.findall(r"ikea.com/\w+/\w+/cat/-\d+", self.url)) == 0:
            raise ValidationError(_("Invalid category URL"))
